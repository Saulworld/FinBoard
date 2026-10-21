"""One local process, isolated storage, verified backup before serving."""

from pathlib import Path
import json, os, secrets, socket, sys, threading, time, urllib.request, webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.local_backup import offline_lock, create_snapshot


def main(open_browser=True):
    os.chdir(ROOT)
    from app.config import get_settings

    settings = get_settings()
    if settings.port == 18010 or not 1024 <= settings.port <= 65535:
        raise RuntimeError("新版端口不能使用原项目的18010。")
    metadata = ROOT / ".runtime/server.json"
    url = f"http://127.0.0.1:{settings.port}"
    print("访问地址：" + url, flush=True)
    # Reopening the launcher should reuse this project's healthy service.
    running = False
    try:
        current = json.loads(metadata.read_text(encoding="utf-8"))
        if Path(current["root"]).resolve() == ROOT and current["port"] == settings.port:
            with urllib.request.urlopen(url + "/api/local/health", timeout=2) as response:
                health = json.load(response)
                running = health.get("status") == "ok" and health.get("edition") == "local-glass"
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if running:
        print("程序已运行，可直接打开上面的地址。", flush=True)
        if open_browser:
            webbrowser.open(url)
        return
    with offline_lock():
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", settings.port))
        print("正在校验并备份当前项目…", flush=True)
        create_snapshot("before-start", "full")
        token = secrets.token_urlsafe(32)
        os.environ["FINBOARD_LOCAL_STOP_TOKEN"] = token
        metadata.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "port": settings.port,
                    "root": str(ROOT),
                    "token": token,
                }
            ),
            encoding="utf-8",
        )
        import uvicorn
        from app.main import app

        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=settings.port,
                workers=1,
                log_level="info",
                access_log=False,
            )
        )
        app.state.local_server = server
        def open_when_ready():
            for _ in range(80):
                if server.should_exit:
                    return
                try:
                    with urllib.request.urlopen(
                        url + "/api/local/health", timeout=0.5
                    ) as response:
                        if json.load(response).get("edition") == "local-glass":
                            webbrowser.open(url)
                            return
                except Exception:
                    time.sleep(0.25)

        if open_browser:
            threading.Thread(target=open_when_ready, daemon=True).start()
        print("新版地址：" + url, flush=True)
        try:
            server.run()
        finally:
            metadata.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main("--no-browser" not in sys.argv)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
