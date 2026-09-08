from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
import html
import subprocess
import sys
import os

from app.db import get_db_session
from app.models import DailyBriefing, DailyReport
from app.config import PROJECT_ROOT

router = APIRouter(tags=["briefing"])


def _deduplicate_report_formats(reports: list[DailyReport]) -> list[DailyReport]:
    """Show one entry per logical report, preferring the richer HTML version."""
    selected: dict[str, DailyReport] = {}
    for report in reports:
        existing = selected.get(report.title)
        if existing is None or (report.file_type == "html" and existing.file_type != "html"):
            selected[report.title] = report
    return sorted(selected.values(), key=lambda item: (item.category, item.title))


def _extract_card_around_match(report_content: str, match_index: int) -> str | None:
    """Extract the stock card that contains a confirmed ticker match."""
    start_idx = report_content.rfind('<div class="row stock"', 0, match_index)
    if start_idx == -1:
        start_idx = report_content.rfind('<div style="padding:26px', 0, match_index)
    if start_idx == -1:
        return None

    next_card_idx = report_content.find('<div class="row stock"', start_idx + 20)
    if next_card_idx == -1:
        next_card_idx = report_content.find('<div style="padding:26px', start_idx + 20)
    if next_card_idx == -1:
        next_card_idx = report_content.find('<div class="sec"', start_idx + 20)
    if next_card_idx == -1:
        next_card_idx = report_content.find('</body>', start_idx + 20)

    return (
        report_content[start_idx:next_card_idx].strip()
        if next_card_idx != -1
        else report_content[start_idx:].strip()
    )


def _find_stock_card_html(reports: list[str], ticker: str) -> str | None:
    """Find a stock card without letting a news mention shadow its exact header."""
    exact_header = f" {ticker} ｜"
    for report_content in reports:
        match_index = report_content.find(exact_header)
        if match_index != -1:
            card_html = _extract_card_around_match(report_content, match_index)
            if card_html:
                return card_html

    # Compatibility fallbacks are evaluated only after every report has been
    # checked for the exact card header. This prevents headlines such as
    # "MSFT ... AVGO In Focus" from returning the preceding MSFT card.
    for marker in (f"【{ticker}】", f" {ticker} "):
        for report_content in reports:
            match_index = report_content.find(marker)
            if match_index != -1:
                card_html = _extract_card_around_match(report_content, match_index)
                if card_html:
                    return card_html
    return None

@router.get("/daily-briefing", response_class=HTMLResponse)
def page_daily_briefing(
    request: Request,
    date: str | None = None,
    q: str | None = None,
    tab: str | None = None,
    session: Session = Depends(get_db_session)
):
    templates = request.app.state.templates
    available_dates = session.scalars(
        select(DailyBriefing.date).distinct().order_by(DailyBriefing.date.desc())
    ).all()

    if not available_dates:
        available_dates = session.scalars(
            select(DailyReport.date).distinct().order_by(DailyReport.date.desc())
        ).all()

    current_date = date or (available_dates[0] if available_dates else None)

    briefings = []
    reports = []

    if q:
        query_str = f"%{q.strip()}%"
        briefings = session.scalars(
            select(DailyBriefing)
            .where(
                (DailyBriefing.ticker.ilike(query_str)) |
                (DailyBriefing.change_reason.ilike(query_str))
            )
            .order_by(DailyBriefing.date.desc(), DailyBriefing.ticker.asc())
        ).all()
    elif current_date:
        briefings = session.scalars(
            select(DailyBriefing)
            .where(DailyBriefing.date == current_date)
            .order_by(DailyBriefing.ticker.asc())
        ).all()

        report_rows = session.scalars(
            select(DailyReport)
            .where(DailyReport.date == current_date)
            .order_by(DailyReport.category.asc(), DailyReport.title.asc())
        ).all()
        reports = _deduplicate_report_formats(list(report_rows))

    actions_summary = {}
    for b in briefings:
        actions_summary[b.action] = actions_summary.get(b.action, 0) + 1

    return templates.TemplateResponse(
        "daily_briefing.html",
        {
            "request": request,
            "active_page": "daily-briefing",
            "page_title": "每日简报",
            "briefings": briefings,
            "reports": reports,
            "available_dates": available_dates,
            # Keep the names expected by the existing template.  The aliases
            # below avoid rendering an empty state after the router split.
            "selected_date": current_date,
            "q": q or "",
            "current_date": current_date,
            "search_query": q or "",
            "actions_summary": actions_summary,
            "active_tab": tab or "evaluation-tab"
        }
    )

@router.get("/api/report/{report_id}", response_class=JSONResponse)
def api_report_content(report_id: int, session: Session = Depends(get_db_session)):
    report = session.get(DailyReport, report_id)
    if not report:
        return JSONResponse({"error": "Report not found"}, status_code=404)
    return JSONResponse({"content": report.content, "file_type": report.file_type})

@router.get("/api/briefing/stock-card", response_class=JSONResponse)
def api_stock_card_html(
    ticker: str,
    date: str | None = None,
    session: Session = Depends(get_db_session)
):
    ticker_upper = ticker.strip().upper()
    
    if not date:
        date = session.execute(
            select(DailyBriefing.date)
            .where(DailyBriefing.ticker == ticker_upper)
            .order_by(DailyBriefing.date.desc())
            .limit(1)
        ).scalar_one_or_none()
        
    if not date:
        date = session.execute(
            select(DailyReport.date)
            .where(DailyReport.file_type == "html")
            .order_by(DailyReport.date.desc())
            .limit(1)
        ).scalar_one_or_none()
        
    if not date:
        return JSONResponse({"status": "error", "message": "No date found"}, status_code=404)

    reports = session.scalars(
        select(DailyReport.content)
        .where(DailyReport.date == date, DailyReport.file_type == "html")
    ).all()

    card_html = _find_stock_card_html(list(reports), ticker_upper)

    if card_html:
        return JSONResponse({
            "status": "success",
            "ticker": ticker_upper,
            "date": date,
            "html": card_html
        })

    briefing = session.execute(
        select(DailyBriefing)
        .where(DailyBriefing.ticker == ticker_upper, DailyBriefing.date == date)
    ).scalar_one_or_none()

    if briefing:
        price_str = f"${briefing.price:.2f}" if briefing.price else "--"
        fallback_html = f"""
<div class="row stock" style="padding:26px;background:#ffffff;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,0.06);font-size:16px;line-height:1.85;">
  <div style="font-weight:800;font-size:22px;margin-bottom:14px;color:#1a73e8;">
    🏷️ {html.escape(briefing.ticker)} ｜ 日期：{briefing.date}
  </div>
  <div style="margin-bottom:18px;background:#f8f9fa;padding:16px 20px;border-radius:8px;border-left:6px solid #1a73e8;line-height:1.85;font-size:16px;">
    <div style="font-size:18px;margin-bottom:8px;">🎯 <b>操作决策：【{html.escape(briefing.action)}】</b> 现价 {price_str}</div>
    <div style="margin-top:8px;"><b>核心理由：</b>{html.escape(briefing.change_reason or '详见每日全量分析报告')}</div>
    <div style="margin-top:8px;"><b>价格计划：</b>{html.escape(briefing.buy_range or '严格遵守交易纪律')}</div>
  </div>
</div>
"""
        return JSONResponse({
            "status": "success",
            "ticker": ticker_upper,
            "date": date,
            "html": fallback_html
        })

    return JSONResponse({"status": "error", "message": f"Card not found for {ticker_upper} on {date}"}, status_code=404)

@router.post("/api/briefing/refresh", response_class=JSONResponse)
@router.post("/api/refresh-briefing", response_class=JSONResponse, include_in_schema=False)
def api_refresh_briefing(session: Session = Depends(get_db_session)):
    try:
        from app.importer import run_import
        results = run_import(session)
        return JSONResponse({
            "status": "success",
            "imported_briefings": results["briefings"],
            "imported_reports": results["reports"]
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
