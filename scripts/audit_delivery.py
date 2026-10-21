"""Read-only comparison of the original checkout and delivered business data."""

import ast
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/verification"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def routes(root):
    result = set()
    for path in (root / "app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr in {"get", "post", "put", "patch", "delete"}
                    and dec.args
                    and isinstance(dec.args[0], ast.Constant)
                    and isinstance(dec.args[0].value, str)
                ):
                    result.add(dec.func.attr.upper() + " " + dec.args[0].value)
    return result


def main():
    marker_path = ROOT / "LOCAL_EDITION.json"
    if marker_path.exists() and json.loads(marker_path.read_text(encoding="utf-8")).get("data_policy") == "canonical-local":
        raise SystemExit("此脚本仅核对迁移前的初始副本；当前主项目请运行scripts/audit_canonical.py。不会据此回滚用户数据。")
    baseline = json.loads((OUT / "source-baseline.json").read_text(encoding="utf-8"))
    source = Path(baseline["source"])
    source_changed = []
    data_changed = []
    data_files = []
    for relative, expected in baseline["files"].items():
        original = source / relative
        if not original.is_file() or digest(original) != expected["sha256"]:
            source_changed.append(relative)
        if Path(relative).parent.as_posix() == "data":
            delivered = ROOT / relative
            data_files.append(relative)
            if not delivered.is_file() or digest(delivered) != expected["sha256"]:
                data_changed.append(relative)
    data_added = sorted(
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "data").iterdir()
        if p.is_file() and p.relative_to(ROOT).as_posix() not in data_files
    )
    with closing(
        sqlite3.connect((ROOT / "data/portfolio.db").as_uri() + "?mode=ro", uri=True)
    ) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {
            name: db.execute(
                'SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"'
            ).fetchone()[0]
            for name in baseline["sqlite_counts"]
        }
    original_routes, current_routes = routes(source), routes(ROOT)
    from app.config import DATA_DIR, DATABASE_PATH, get_settings

    settings = get_settings()
    regression = (OUT / "regression.log").read_text(encoding="utf-8-sig")
    interactions = json.loads((OUT / "interactions.json").read_text(encoding="utf-8"))
    result = {
        "created_at": datetime.now().astimezone().isoformat(),
        "source": str(source),
        "destination": str(ROOT),
        "source_baseline_files_checked": len(baseline["files"]),
        "source_changed_or_missing": source_changed,
        "delivered_data_files_checked": len(data_files),
        "delivered_data_changed_or_missing": data_changed,
        "delivered_data_added": data_added,
        "sqlite_integrity": integrity,
        "sqlite_counts": counts,
        "sqlite_counts_match_baseline": counts == baseline["sqlite_counts"],
        "original_route_count": len(original_routes),
        "removed_routes": sorted(original_routes - current_routes),
        "added_routes": sorted(current_routes - original_routes),
        "data_directory": str(DATA_DIR),
        "database": str(DATABASE_PATH),
        "host": settings.host,
        "port": settings.port,
        "regression_pass": "Ran 24 tests" in regression
        and regression.rstrip().endswith("OK"),
        "browser_interactions": interactions,
        "limitations": [
            "Remote data providers are not exhaustively verified.",
            "Route preservation is a static inventory; browser checks cover selected critical workflows.",
        ],
    }
    final_backup = OUT / "release-backup.json"
    if final_backup.exists():
        result["release_snapshot"] = json.loads(
            final_backup.read_text(encoding="utf-8-sig")
        )
    result["result"] = (
        "PASS"
        if (
            not source_changed
            and not data_changed
            and not data_added
            and integrity == "ok"
            and result["sqlite_counts_match_baseline"]
            and not result["removed_routes"]
            and result["regression_pass"]
            and interactions["result"] == "PASS"
            and DATA_DIR == ROOT / "data"
            and settings.port == 18011
        )
        else "FAIL"
    )
    (OUT / "delivery-audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT))
    main()
