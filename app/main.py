import os
import sys
import logging
import asyncio
import secrets
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import init_db, get_db_session, SessionLocal, engine
from app.models import WatchlistItem, DailyBriefing, DailyReport
from app.services import get_market_data_service
from app.utils import (
    register_jinja_globals,
    load_phone_records,
    calculate_phone_status,
    MARKET_LABELS,
)

from app.routers import (
    briefing_router,
    stock_router,
    portfolio_router,
    phones_router,
    cards_router,
    wallet_cards_router,
    ai_monitor_router,
    overseas_documents_router,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "app" / "static"
TEMPLATES_DIR = PROJECT_ROOT / "app" / "templates"
APP_NAME = "FinBoard"
REFRESH_INTERVAL_SECONDS = 30

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("finboard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    init_db()

    # Import only on the user's explicit refresh action, never during startup.
    app.state.mutation_lock = asyncio.Lock()
    logger.info("Application startup complete.")
    try:
        yield
    finally:
        engine.dispose()
        logger.info("Application shutdown.")


app = FastAPI(title=APP_NAME, lifespan=lifespan)


@app.middleware("http")
async def protect_local_data(request: Request, call_next):
    from urllib.parse import urlsplit
    from app.config import DATA_DIR
    from scripts.local_backup import create_snapshot

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin:
            parsed = urlsplit(origin)
            if (
                parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.port != request.url.port
            ):
                return JSONResponse(
                    {"message": "请从新版的本地页面执行此操作。"}, status_code=403
                )
        if not hasattr(app.state, "mutation_lock"):
            app.state.mutation_lock = asyncio.Lock()
        async with app.state.mutation_lock:
            if (
                not request.url.path.startswith("/api/local/")
                and DATA_DIR == PROJECT_ROOT / "data"
            ):
                try:
                    await asyncio.to_thread(
                        create_snapshot, "before-change:" + request.url.path, "data"
                    )
                except Exception:
                    logger.exception("Backup before change failed")
                    return JSONResponse(
                        {
                            "message": "操作前备份失败，本次数据未修改。请检查本地磁盘和备份目录。"
                        },
                        status_code=503,
                    )
            response = await call_next(request)
    else:
        response = await call_next(request)
    if not request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/local/health")
def local_health():
    return {"status": "ok", "edition": "local-glass"}


@app.get("/api/local/backups")
def local_backups():
    from scripts.local_backup import list_snapshots

    return {"backups": list_snapshots()[:30]}


@app.post("/api/local/backup")
async def local_backup():
    from scripts.local_backup import create_snapshot

    result = await asyncio.to_thread(create_snapshot, "manual-from-app", "full")
    return result


@app.post("/api/local/stop")
async def local_stop(request: Request):
    expected = os.getenv("FINBOARD_LOCAL_STOP_TOKEN", "")
    if not expected or not secrets.compare_digest(
        request.headers.get("x-local-token", ""), expected
    ):
        return JSONResponse({"message": "无效的本地停止指令。"}, status_code=403)
    server = getattr(app.state, "local_server", None)
    if server is None:
        return JSONResponse(
            {"message": "当前服务未通过新版启动器启动。"}, status_code=409
        )
    server.should_exit = True
    return {"status": "stopping"}


# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates setup
from app.expiry_alerts import wallet_alerts, phone_alerts

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
register_jinja_globals(templates.env)
templates.env.globals.update(wallet_alerts=wallet_alerts, phone_alerts=phone_alerts)
templates.env.globals["app_name"] = APP_NAME
app.state.templates = templates

# Register modular routers
app.include_router(briefing_router)
app.include_router(stock_router)
app.include_router(portfolio_router)
app.include_router(phones_router)
app.include_router(cards_router)
app.include_router(wallet_cards_router)
app.include_router(ai_monitor_router)
app.include_router(overseas_documents_router)


@app.get("/", response_class=HTMLResponse)
def page_dashboard(
    request: Request,
    notice: str | None = None,
    error: str | None = None,
    session: Session = Depends(get_db_session),
):
    items = session.scalars(
        select(WatchlistItem).order_by(WatchlistItem.updated_at.desc())
    ).all()
    service = get_market_data_service()
    watchlist_rows = [
        {
            "id": item.id,
            "input_symbol": item.input_symbol,
            "symbol": item.symbol,
            "market": item.market,
            "market_label": MARKET_LABELS.get(item.market, item.market),
            "name": item.name or item.symbol,
            "note": item.note,
            "quote": service.get_empty_quote(item.symbol, item.market),
        }
        for item in items
    ]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "market_labels": MARKET_LABELS,
            "watchlist_rows": watchlist_rows,
            "notice": notice,
            "error": error,
            "refresh_interval": REFRESH_INTERVAL_SECONDS,
            "page_title": "股票总览",
        },
    )


@app.get("/local-maintenance", response_class=HTMLResponse)
def local_maintenance(request: Request):
    return templates.TemplateResponse(
        "local_maintenance.html",
        {"request": request, "active_page": "maintenance", "page_title": "备份与记录"},
    )


if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings

    settings = get_settings()
    from scripts.run_local import main

    main()
