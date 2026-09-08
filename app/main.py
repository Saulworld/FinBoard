import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import init_db, get_db_session, SessionLocal
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
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "app" / "static"
TEMPLATES_DIR = PROJECT_ROOT / "app" / "templates"
APP_NAME = "FinBoard"
REFRESH_INTERVAL_SECONDS = 30

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("finboard")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    init_db()
    
    with SessionLocal() as db_session:
        try:
            briefing_count = db_session.query(DailyBriefing).count()
            if briefing_count == 0:
                from app.importer import run_import
                run_import(db_session)
        except Exception as e:
            logger.warning(f"Auto-import briefings failed: {e}")
            
    logger.info("Application startup complete.")
    yield
    logger.info("Application shutdown.")

app = FastAPI(title=APP_NAME, lifespan=lifespan)

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

@app.get("/", response_class=HTMLResponse)
def page_dashboard(
    request: Request,
    notice: str | None = None,
    error: str | None = None,
    session: Session = Depends(get_db_session),
):
    items = session.scalars(select(WatchlistItem).order_by(WatchlistItem.updated_at.desc())).all()
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
            "page_title": "仪表盘概览"
        }
    )

if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
