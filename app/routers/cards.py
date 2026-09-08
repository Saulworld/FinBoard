from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.json_store import json_file_transaction
from app.utils import (
    CARDS_FILE,
    build_redirect_url,
    capitalize_english,
    load_card_options,
    load_card_records,
    remove_cjk_latin_spaces,
    save_card_options,
    save_card_records,
)


router = APIRouter(tags=["cards"])


def _clean(value: str) -> str:
    return capitalize_english(remove_cjk_latin_spaces((value or "").strip()))


@router.get("/cards", response_class=HTMLResponse)
def list_cards(request: Request, notice: str | None = None, error: str | None = None):
    return request.app.state.templates.TemplateResponse(
        "cards.html",
        {
            "request": request, "active_page": "cards", "page_title": "境外工具",
            "cards": load_card_records(), "options": load_card_options(),
            "notice": notice, "error": error,
        },
    )


@router.post("/cards/add")
def add_card(
    name: str = Form(...), kyc_method: str = Form(""), kyc_provider: str = Form("--"),
    login_method: str = Form(""), type: str = Form(""), country: str = Form(""),
    phone: str = Form(""), address: str = Form(""), note: str = Form(""),
    account_provider: str = Form("--"), color: str = Form(""),
):
    with json_file_transaction(CARDS_FILE):
        cards = load_card_records()
        next_id = max((int(card.get("id", 0)) for card in cards), default=0) + 1
        cards.append(
            {
                "id": next_id, "name": _clean(name),
                "kyc_method": "CNID" if country == "中国" else "CN护照",
                "kyc_provider": _clean(kyc_provider), "login_method": _clean(login_method),
                "type": _clean(type), "country": _clean(country), "phone": phone.strip(),
                "address": _clean(address), "note": _clean(note),
                "account_provider": remove_cjk_latin_spaces(account_provider.strip()) or "--",
                "color": color.strip(), "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        save_card_records(cards)
    return RedirectResponse(build_redirect_url("/cards", notice="境外工具已添加。"), status_code=303)


@router.post("/cards/{card_id}/update", response_class=JSONResponse)
def update_card(
    card_id: int, name: str = Form(...), kyc_method: str = Form(""),
    kyc_provider: str = Form("--"), login_method: str = Form(""), type: str = Form(""),
    country: str = Form(""), phone: str = Form(""), address: str = Form(""),
    note: str = Form(""), account_provider: str = Form("--"), color: str = Form(""),
):
    found = False
    with json_file_transaction(CARDS_FILE):
        cards = load_card_records()
        for card in cards:
            if int(card.get("id", 0)) == card_id:
                card.update(
                    name=_clean(name), kyc_method="CNID" if country == "中国" else "CN护照",
                    kyc_provider=_clean(kyc_provider), login_method=_clean(login_method),
                    type=_clean(type), country=_clean(country), phone=phone.strip(),
                    address=_clean(address), note=_clean(note),
                    account_provider=remove_cjk_latin_spaces(account_provider.strip()) or "--",
                    color=color.strip(),
                )
                found = True
                break
        if found:
            save_card_records(cards)
    return JSONResponse({"status": "success"} if found else {"status": "error", "message": "记录不存在"}, status_code=200 if found else 404)


@router.post("/cards/{card_id}/delete", response_class=JSONResponse)
def delete_card(card_id: int):
    with json_file_transaction(CARDS_FILE):
        cards = load_card_records()
        kept = [card for card in cards if int(card.get("id", 0)) != card_id]
        if len(kept) == len(cards):
            return JSONResponse({"status": "error", "message": "记录不存在"}, status_code=404)
        save_card_records(kept)
    return JSONResponse({"status": "success"})


@router.get("/api/cards/options", response_class=JSONResponse)
def get_card_options():
    return JSONResponse(load_card_options())


@router.post("/api/cards/options", response_class=JSONResponse)
async def set_card_options(request: Request):
    save_card_options(await request.json())
    return JSONResponse({"status": "success"})
