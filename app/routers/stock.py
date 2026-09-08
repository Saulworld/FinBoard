from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import math
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.models import DailyBriefing, Holding, WatchlistItem
from app.services import get_market_data_service
from app.utils import get_preferred_providers, normalize_market, normalize_symbol, translate_text


router = APIRouter(tags=["stock"])


def _sanitize(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


@router.get("/stock", response_class=HTMLResponse)
def stock_detail(
    request: Request,
    symbol: str,
    market: str = "US",
    session: Session = Depends(get_db_session),
):
    market = normalize_market(market)
    normalized_symbol = normalize_symbol(symbol, market)
    name = session.execute(
        select(WatchlistItem.name).where(
            WatchlistItem.symbol == normalized_symbol, WatchlistItem.market == market
        )
    ).scalar_one_or_none()
    if not name:
        name = session.execute(
            select(Holding.name).where(Holding.symbol == normalized_symbol, Holding.market == market)
        ).scalar_one_or_none()
    briefing_history = session.scalars(
        select(DailyBriefing)
        .where(DailyBriefing.ticker == normalized_symbol)
        .order_by(DailyBriefing.date.desc())
        .limit(20)
    ).all()
    detail = {
        "symbol": normalized_symbol,
        "input_symbol": symbol.strip().upper(),
        "market": market,
        "name": name or normalized_symbol,
    }
    return request.app.state.templates.TemplateResponse(
        "stock_detail.html",
        {
            "request": request, "active_page": "dashboard", "page_title": detail["name"],
            "detail": detail, "briefing_history": briefing_history,
        },
    )


@router.get("/api/stock/detail", response_class=JSONResponse)
def api_stock_detail(request: Request, symbol: str, market: str = "US", refresh: bool = False):
    try:
        detail = get_market_data_service().get_stock_detail(
            symbol, market, get_preferred_providers(request), bypass_cache=refresh
        )
        return JSONResponse(_sanitize(jsonable_encoder(detail)))
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)


@router.get("/api/quote", response_class=JSONResponse)
def api_quote(request: Request, symbol: str, market: str = "US"):
    quote = get_market_data_service().get_quote(symbol, market, get_preferred_providers(request))
    return JSONResponse(_sanitize(jsonable_encoder(quote)))


@router.get("/api/quotes/batch", response_class=JSONResponse)
def api_quotes_batch(request: Request, pairs: str):
    parsed = []
    keys = []
    for raw in pairs.split(","):
        value = raw.strip()
        if not value or ":" not in value:
            continue
        symbol, market = value.rsplit(":", 1)
        market = normalize_market(market)
        symbol = normalize_symbol(symbol, market)
        parsed.append((symbol, market))
        keys.append(f"{symbol}:{market}")
    quotes = get_market_data_service().get_quotes_batch(parsed, get_preferred_providers(request))
    payload = {
        key: _sanitize(jsonable_encoder(quotes.get(pair)))
        for key, pair in zip(keys, parsed)
        if quotes.get(pair) is not None
    }
    return JSONResponse({"quotes": payload})


@router.post("/api/translate/news", response_class=JSONResponse)
async def api_translate_news(request: Request):
    news = await request.json()
    if not isinstance(news, list):
        return JSONResponse({"error": "请求必须是新闻数组"}, status_code=400)

    def _translate(item: dict[str, Any]) -> dict[str, Any]:
        result = dict(item)
        result["title"] = translate_text(str(item.get("title") or ""))
        result["summary"] = translate_text(str(item.get("summary") or ""))
        return result

    with ThreadPoolExecutor(max_workers=min(max(len(news), 1), 10)) as executor:
        translated = list(executor.map(_translate, news))
    return JSONResponse({"news": translated})
