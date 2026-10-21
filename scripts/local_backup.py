"""Verified local snapshots. No imports from app: backup/restore works when app is broken."""

from __future__ import annotations
import argparse, hashlib, json, os, shutil, sqlite3, sys, tempfile, zipfile
from contextlib import contextmanager, closing
from datetime import datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
TOP_DIRS = {"app", "data", "scripts", "docs", ".agents", "tests"}
ROOT_FILES = {
    "LOCAL_EDITION.json",
    "AGENTS.md",
    "CHANGELOG.md",
    "README.md",
    "LICENSE",
    ".env",
    ".env.example",
    ".gitignore",
    "requirements.txt",
    "requirements-local.lock.txt",
    "start_local.ps1",
    "start_local.bat",
    "启动新版.bat",
    "备份新版.bat",
    "恢复新版.bat",
    "停止新版.bat",
    "开始使用.txt",
}
EXCLUDE = {"backups", "__pycache__", "verification", ".runtime", ".pytest_cache"}


def ensure_local(root=ROOT):
    root = Path(root).resolve()
    marker = root / "LOCAL_EDITION.json"
    if not marker.is_file():
        raise RuntimeError("缺少新版标记，拒绝操作该目录。")
    source = Path(
        json.loads(marker.read_text(encoding="utf-8"))["source_root"]
    ).resolve()
    if root == source or root.is_relative_to(source):
        raise RuntimeError("拒绝操作受保护的迁移来源或归档目录。")
    return root


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def allowed(name, scope):
    p = PurePosixPath(name)
    if (
        not name
        or p.is_absolute()
        or ".." in p.parts
        or "\\" in name
        or ":" in name
        or any(s in EXCLUDE for s in p.parts)
    ):
        return False
    return (
        (p.parts[0] == "data")
        if scope == "data"
        else (p.parts[0] in TOP_DIRS or (len(p.parts) == 1 and name in ROOT_FILES))
    )


def files_for(root, scope):
    for directory, dirs, names in os.walk(root):
        base = Path(directory)
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in EXCLUDE
            and not (
                base == root and d not in ({"data"} if scope == "data" else TOP_DIRS)
            )
        )
        for name in sorted(names):
            p = base / name
            rel = p.relative_to(root).as_posix()
            if allowed(rel, scope) and not p.name.endswith(
                ("-wal", "-shm", ".lock", ".tmp")
            ):
                if p.is_symlink() or not p.resolve().is_relative_to(root):
                    raise RuntimeError("快照不允许链接到项目外部。")
                yield p, rel


def log_event(root, event, **details):
    path = root / "backups/local/operations.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "time": datetime.now().astimezone().isoformat(),
                    "event": event,
                    **details,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


@contextmanager
def offline_lock(root=ROOT):
    root = ensure_local(root)
    folder = root / ".runtime"
    folder.mkdir(exist_ok=True)
    with (folder / "process.lock").open("a+b") as f:
        if f.tell() == 0:
            f.write(b"0")
            f.flush()
        f.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(
                "新版正在运行，请先停止后恢复；运行中备份请使用页面的“立即备份”。"
            ) from exc
        try:
            yield
        finally:
            f.seek(0)
            if os.name == "nt":
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


def create_snapshot(reason="manual", scope="full", root=ROOT):
    root = ensure_local(root)
    if scope not in {"data", "full"}:
        raise ValueError("Invalid snapshot scope")
    target = root / "backups/local"
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dest = target / f"{stamp}-{scope}.zip"
    pending = dest.with_suffix(".partial")
    manifest = {
        "format": 1,
        "created_at": datetime.now().astimezone().isoformat(),
        "scope": scope,
        "reason": reason,
        "files": {},
    }
    try:
        with tempfile.TemporaryDirectory(prefix="snapshot-", dir=target) as temporary:
            with zipfile.ZipFile(
                pending, "w", zipfile.ZIP_DEFLATED, compresslevel=1
            ) as z:
                for p, rel in files_for(root, scope):
                    use = p
                    if p.suffix in {".db", ".sqlite", ".sqlite3"}:
                        use = Path(temporary) / (
                            hashlib.sha256(rel.encode()).hexdigest() + ".db"
                        )
                        with (
                            closing(
                                sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
                            ) as source,
                            closing(sqlite3.connect(use)) as copy,
                        ):
                            source.backup(copy)
                            if copy.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                                raise RuntimeError("数据库完整性检查失败。")
                    before = sha(use)
                    z.write(use, rel)
                    if sha(use) != before:
                        raise RuntimeError("备份期间文件发生变化，请重试。")
                    manifest["files"][rel] = {
                        "sha256": before,
                        "size": use.stat().st_size,
                    }
                z.writestr(
                    "SNAPSHOT.json", json.dumps(manifest, ensure_ascii=False, indent=2)
                )
        verify_snapshot(pending)
        os.replace(pending, dest)
        log_event(
            root,
            "backup",
            file=dest.name,
            scope=scope,
            reason=reason,
            files=len(manifest["files"]),
        )
        return {
            "name": dest.name,
            "path": str(dest),
            "scope": scope,
            "created_at": manifest["created_at"],
            "files": len(manifest["files"]),
            "bytes": dest.stat().st_size,
        }
    finally:
        pending.unlink(missing_ok=True)


def verify_snapshot(path):
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read("SNAPSHOT.json"))
        if manifest.get("format") != 1 or manifest.get("scope") not in {"full", "data"}:
            raise RuntimeError("快照格式无效。")
        files = manifest.get("files", {})
        if not files:
            raise RuntimeError("空快照不可恢复。")
        if len(z.namelist()) != len(set(z.namelist())):
            raise RuntimeError("快照包含重复文件。")
        if set(z.namelist()) != set(files) | {"SNAPSHOT.json"}:
            raise RuntimeError("快照目录与校验清单不一致。")
        for name, meta in files.items():
            if not allowed(name, manifest["scope"]):
                raise RuntimeError("快照包含越界路径。")
            data = z.read(name)
            if (
                len(data) != meta["size"]
                or hashlib.sha256(data).hexdigest() != meta["sha256"]
            ):
                raise RuntimeError("快照校验失败。")
        return manifest


def list_snapshots(root=ROOT):
    root = ensure_local(root)
    items = []
    for p in sorted((root / "backups/local").glob("*.zip"), reverse=True):
        try:
            with zipfile.ZipFile(p) as z:
                m = json.loads(z.read("SNAPSHOT.json"))
            items.append(
                {
                    "name": p.name,
                    "created_at": m["created_at"],
                    "scope": m["scope"],
                    "reason": m["reason"],
                    "bytes": p.stat().st_size,
                }
            )
        except (OSError, ValueError, KeyError, zipfile.BadZipFile):
            continue
    return items


def restore_snapshot(name, root=ROOT):
    root = ensure_local(root)
    if Path(name).name != name:
        raise RuntimeError("只接受本项目备份文件名。")
    source = root / "backups/local" / name
    manifest = verify_snapshot(source)
    # The local boundary is part of every restorable snapshot, not the archived original checkout.
    if manifest["scope"] == "full":
        with zipfile.ZipFile(source) as z:
            marker = json.loads(z.read("LOCAL_EDITION.json"))
            if marker.get("edition") != "local-glass":
                raise RuntimeError("不能将旧项目代码恢复为新版。")
            protected = Path(marker["source_root"]).resolve()
            if root == protected or root.is_relative_to(protected):
                raise RuntimeError("此快照属于迁移前目录，不能在当前主项目直接恢复。")
    safety = create_snapshot("before-restore", manifest["scope"], root)
    with tempfile.TemporaryDirectory(prefix="restore-", dir=root / ".runtime") as tmp:
        stage = Path(tmp) / "stage"
        originals = Path(tmp) / "originals"
        stage.mkdir()
        originals.mkdir()
        with zipfile.ZipFile(source) as z:
            for rel in manifest["files"]:
                target = root / rel
                if not target.resolve().is_relative_to(root) or target.is_symlink():
                    raise RuntimeError("恢复路径越界。")
                p = stage / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(z.read(rel))
                if p.suffix in {".db", ".sqlite", ".sqlite3"}:
                    with closing(
                        sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
                    ) as db:
                        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise RuntimeError("恢复数据库校验失败。")
        current = {rel: p for p, rel in files_for(root, manifest["scope"])}
        changed = []
        try:
            for rel in sorted(set(current) | set(manifest["files"])):
                target = root / rel
                if not target.resolve().is_relative_to(root):
                    raise RuntimeError("恢复路径越界。")
                if target.exists():
                    saved = originals / rel
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, saved)
                changed.append(rel)
                if rel in manifest["files"]:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(stage / rel, target)
                elif target.exists():
                    target.unlink()
        except Exception:
            for rel in reversed(changed):
                saved = originals / rel
                target = root / rel
                if saved.exists():
                    os.replace(saved, target)
                else:
                    target.unlink(missing_ok=True)
            log_event(root, "restore-failed", file=name, safety=safety["name"])
            raise
    log_event(root, "restore", file=name, safety=safety["name"])
    return {"restored": name, "safety_backup": safety["name"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["backup", "list", "verify", "restore"])
    parser.add_argument("name", nargs="?")
    parser.add_argument("--scope", choices=["full", "data"], default="full")
    parser.add_argument("--reason", default="manual")
    args = parser.parse_args()
    if args.action == "list":
        result = list_snapshots()
    elif args.action == "verify":
        if not args.name or Path(args.name).name != args.name:
            raise RuntimeError("请填写本地备份文件名。")
        m = verify_snapshot(ROOT / "backups/local" / args.name)
        result = {"verified": args.name, "files": len(m["files"])}
    else:
        with offline_lock():
            if args.action == "backup":
                result = create_snapshot(args.reason, args.scope)
            else:
                if not args.name:
                    raise RuntimeError("请先用list查看备份文件名。")
                if (
                    input("恢复前会自动备份现状。输入 RESTORE 确认：").strip()
                    != "RESTORE"
                ):
                    raise RuntimeError("已取消。")
                result = restore_snapshot(args.name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
