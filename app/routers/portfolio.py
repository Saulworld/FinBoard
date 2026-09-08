from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db_session
from app.models import Holding, HoldingTransaction, WatchlistItem
from app.portfolio import PortfolioEntry, calculate_portfolio_totals
from app.services import get_market_data_service
from app.utils import (
    MARKET_LABELS,
    build_redirect_url,
    format_money,
    get_market_currency,
    get_preferred_providers,
    normalize_market,
    normalize_symbol,
    parse_holdings_text,
)


router = APIRouter(tags=["portfolio"])
settings = get_settings()
SUPPORTED_PORTFOLIO_CURRENCIES = ("CNY", "USD", "HKD")


@router.post("/watchlist")
def add_watchlist(
    symbol: str = Form(...),
    market: str = Form("US"),
    name: str = Form(""),
    note: str = Form(""),
    session: Session = Depends(get_db_session),
):
    market = normalize_market(market)
    normalized_symbol = normalize_symbol(symbol, market)
    existing = session.execute(
        select(WatchlistItem).where(
            WatchlistItem.symbol == normalized_symbol,
            WatchlistItem.market == market,
        )
    ).scalar_one_or_none()
    if existing:
        existing.name = name.strip() or existing.name
        existing.note = note.strip()
    else:
        session.add(
            WatchlistItem(
                input_symbol=symbol.strip().upper(),
                symbol=normalized_symbol,
                market=market,
                name=name.strip() or normalized_symbol,
                note=note.strip(),
            )
        )
    session.commit()
    return RedirectResponse(build_redirect_url("/", notice="已保存自选。"), status_code=303)


@router.post("/watchlist/{item_id}/delete")
def delete_watchlist(item_id: int, session: Session = Depends(get_db_session)):
    item = session.get(WatchlistItem, item_id)
    if item:
        session.delete(item)
        session.commit()
    return RedirectResponse(build_redirect_url("/", notice="已移除自选。"), status_code=303)


@router.get("/holdings", response_class=HTMLResponse)
def page_holdings(
    request: Request,
    notice: str | None = None,
    error: str | None = None,
    session: Session = Depends(get_db_session),
):
    templates = request.app.state.templates
    holdings = session.scalars(select(Holding).order_by(Holding.updated_at.desc())).all()
    rows = []
    for holding in holdings:
        currency = get_market_currency(holding.market)
        cost_value = holding.quantity * holding.average_cost
        rows.append(
            {
                "id": holding.id,
                "symbol": holding.symbol,
                "input_symbol": holding.input_symbol,
                "market": holding.market,
                "market_label": MARKET_LABELS.get(holding.market, holding.market),
                "name": holding.name or holding.symbol,
                "quantity": holding.quantity,
                "average_cost": holding.average_cost,
                "average_cost_text": format_money(holding.average_cost, currency),
                "cost_value": cost_value,
                "cost_value_text": format_money(cost_value, currency),
                "note": holding.note,
            }
        )

    transactions = session.scalars(
        select(HoldingTransaction)
        .order_by(HoldingTransaction.date.desc(), HoldingTransaction.created_at.desc())
        .limit(15)
    ).all()
    summary = {
        "holding_count": len(rows),
        "base_currency": settings.portfolio_base_currency,
        "total_cost_text": "加载中...",
        "total_value_text": "加载中...",
        "total_pnl_text": "加载中...",
        "total_pnl_class": "flat",
    }
    return templates.TemplateResponse(
        "holdings.html",
        {
            "request": request,
            "active_page": "holdings",
            "page_kicker": "本地记录",
            "page_title": "持仓记录",
            "market_labels": MARKET_LABELS,
            "rows": rows,
            "summary": summary,
            "portfolio_currencies": SUPPORTED_PORTFOLIO_CURRENCIES,
            "transactions": transactions,
            "notice": notice,
            "error": error,
        },
    )


@router.get("/api/holdings/quotes", response_class=JSONResponse)
def api_holdings_quotes(
    request: Request,
    base_currency: str | None = Query(None),
    session: Session = Depends(get_db_session),
):
    selected_currency = (base_currency or settings.portfolio_base_currency).strip().upper()
    if selected_currency not in SUPPORTED_PORTFOLIO_CURRENCIES:
        return JSONResponse(
            {"error": f"Unsupported base currency: {selected_currency}"},
            status_code=400,
        )

    service = get_market_data_service()
    holdings = session.scalars(select(Holding)).all()
    pairs = [(holding.symbol, holding.market) for holding in holdings]
    quotes_map = service.get_quotes_batch(pairs, get_preferred_providers(request), bypass_cache=False)

    quote_rows = []
    entries = []
    for holding in holdings:
        quote = quotes_map.get((holding.symbol, holding.market))
        cost_value = holding.quantity * holding.average_cost
        cost_currency = get_market_currency(holding.market)
        price = quote.price if quote and quote.price is not None else None
        market_currency = (quote.currency if quote else None) or cost_currency
        market_value = holding.quantity * price if price is not None else None
        pnl_value = market_value - cost_value if market_value is not None and market_currency == cost_currency else None
        entries.append(PortfolioEntry(cost_value, cost_currency, market_value, market_currency))

        price_text = format_money(price, market_currency)
        if quote and quote.market_state == "PRE":
            price_text = f"{price_text} (盘前)"
        elif quote and quote.market_state == "POST":
            price_text = f"{price_text} (盘后)"
        quote_rows.append(
            {
                "symbol": holding.symbol,
                "market": holding.market,
                "price": price,
                "price_text": price_text,
                "market_value_text": format_money(market_value, market_currency),
                "pnl_text": format_money(pnl_value, market_currency),
                "pnl_class": "up" if pnl_value and pnl_value > 0 else "down" if pnl_value and pnl_value < 0 else "flat",
            }
        )

    totals = calculate_portfolio_totals(entries, selected_currency, service.get_exchange_rate)
    if totals.complete:
        total_cost_text = format_money(totals.total_cost, totals.base_currency)
        total_value_text = format_money(totals.total_value, totals.base_currency)
        total_pnl_text = format_money(totals.total_pnl, totals.base_currency)
        total_pnl_class = "up" if totals.total_pnl and totals.total_pnl > 0 else "down" if totals.total_pnl and totals.total_pnl < 0 else "flat"
        error = None
    else:
        total_cost_text = total_value_text = total_pnl_text = "--"
        total_pnl_class = "flat"
        error = f"缺少必要行情或汇率（{'/'.join(totals.missing_currencies)}），已停止生成错误汇总。"

    return JSONResponse(
        {
            "quotes": quote_rows,
            "summary": {
                "base_currency": totals.base_currency,
                "total_cost_text": total_cost_text,
                "total_value_text": total_value_text,
                "total_pnl_text": total_pnl_text,
                "total_pnl_class": total_pnl_class,
                "error": error,
            },
        }
    )


@router.post("/holdings/import")
def import_holdings_text(
    content: str = Form(...),
    default_market: str = Form("US"),
    replace_existing: str | None = Form(None),
    session: Session = Depends(get_db_session),
):
    rows, errors = parse_holdings_text(content, default_market)
    if errors:
        return RedirectResponse(build_redirect_url("/holdings", error="；".join(errors[:3])), status_code=303)
    if replace_existing:
        session.query(Holding).delete()
    for row in rows:
        existing = session.execute(
            select(Holding).where(Holding.symbol == row["symbol"], Holding.market == row["market"])
        ).scalar_one_or_none()
        if existing:
            for field in ("input_symbol", "name", "quantity", "average_cost", "note"):
                if field == "name" and not row[field]:
                    continue
                setattr(existing, field, row[field])
        else:
            session.add(Holding(**row))
    session.commit()
    return RedirectResponse(build_redirect_url("/holdings", notice=f"已导入 {len(rows)} 条持仓。"), status_code=303)


@router.post("/holdings/{holding_id}/delete")
def delete_holding(holding_id: int, session: Session = Depends(get_db_session)):
    holding = session.get(Holding, holding_id)
    if holding:
        session.delete(holding)
        session.commit()
    return RedirectResponse(build_redirect_url("/holdings", notice="已删除持仓记录。"), status_code=303)


@router.post("/holdings/{holding_id}/update")
def update_holding(
    holding_id: int,
    quantity: float = Form(...),
    price: float = Form(...),
    note: str = Form(""),
    session: Session = Depends(get_db_session),
):
    holding = session.get(Holding, holding_id)
    if holding:
        holding.quantity = quantity
        holding.average_cost = price
        holding.note = note.strip()
        session.commit()
    return RedirectResponse(build_redirect_url("/holdings", notice="持仓数据已成功修改。"), status_code=303)


@router.post("/holdings/transaction")
def add_transaction(
    action: str = Form(...),
    market: str = Form("US"),
    symbol: str = Form(...),
    quantity: float | None = Form(None),
    price: float = Form(...),
    note: str = Form(""),
    date: str = Form(...),
    session: Session = Depends(get_db_session),
):
    market = normalize_market(market)
    normalized_symbol = normalize_symbol(symbol, market)
    holding = session.execute(
        select(Holding).where(Holding.symbol == normalized_symbol, Holding.market == market)
    ).scalar_one_or_none()
    tx_quantity = quantity
    name = holding.name if holding else normalized_symbol

    if action == "加仓":
        if quantity is None or quantity <= 0 or price <= 0:
            return RedirectResponse(build_redirect_url("/holdings", error="数量和价格必须大于0。"), status_code=303)
        if holding:
            new_quantity = holding.quantity + quantity
            holding.average_cost = (holding.quantity * holding.average_cost + quantity * price) / new_quantity
            holding.quantity = new_quantity
        else:
            holding = Holding(
                input_symbol=symbol.strip().upper(), symbol=normalized_symbol, market=market,
                name=normalized_symbol, quantity=quantity, average_cost=price, note=note.strip(),
            )
            session.add(holding)
    elif action == "减仓":
        if not holding or quantity is None or quantity <= 0 or quantity > holding.quantity:
            return RedirectResponse(build_redirect_url("/holdings", error="减仓数量无效或超过当前持仓。"), status_code=303)
        holding.quantity -= quantity
        if holding.quantity == 0:
            session.delete(holding)
    elif action == "平仓":
        if not holding:
            return RedirectResponse(build_redirect_url("/holdings", error="没有找到对应持仓。"), status_code=303)
        tx_quantity = holding.quantity
        session.delete(holding)
    else:
        return RedirectResponse(build_redirect_url("/holdings", error="无效的交易动作。"), status_code=303)

    session.add(
        HoldingTransaction(
            symbol=normalized_symbol, market=market, name=name, action=action,
            quantity=tx_quantity, price=price, note=note.strip(), date=date,
        )
    )
    session.commit()
    return RedirectResponse(build_redirect_url("/holdings", notice=f"已执行{action}。"), status_code=303)
