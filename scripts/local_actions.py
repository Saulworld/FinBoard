from pathlib import Path
import json, sys, urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.local_backup import (
    main as backup_main,
    offline_lock,
    create_snapshot,
    list_snapshots,
    restore_snapshot,
)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "backup"
    metadata = ROOT / ".runtime/server.json"
    if action in {"backup", "stop"} and metadata.exists():
        data = json.loads(metadata.read_text(encoding="utf-8"))
        if Path(data["root"]).resolve() != ROOT or data["port"] == 18010:
            raise RuntimeError("新版服务信息不匹配。")
        url = f"http://127.0.0.1:{int(data['port'])}/api/local/" + (
            "stop" if action == "stop" else "backup"
        )
        req = urllib.request.Request(
            url, data=b"", method="POST", headers={"X-Local-Token": data["token"]}
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.load(response)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if action == "stop":
        print("新版当前未运行。")
        return
    with offline_lock():
        if action == "backup":
            result = create_snapshot("manual-launcher", "full")
        else:
            items = list_snapshots()
            if not items:
                raise RuntimeError("没有可用快照。")
            for i, item in enumerate(items, 1):
                print(f"{i}. {item['created_at']} [{item['scope']}] {item['reason']}")
            selected = int(input("输入需要恢复的序号（关闭窗口可取消）："))
            if not 1 <= selected <= len(items):
                raise RuntimeError("序号无效。")
            if input("将自动备份现状。输入 RESTORE 确认恢复：").strip() != "RESTORE":
                print("已取消。")
                return
            result = restore_snapshot(items[selected - 1]["name"])
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
