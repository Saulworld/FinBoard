from __future__ import annotations

from datetime import datetime
import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.bin_database import get_card_bin_info
from app.expiry_alerts import card_expiry_status
from app.json_store import json_file_transaction, load_json, save_json_atomic
from app.utils import (
    WALLET_CARDS_FILE,
    build_redirect_url,
    load_card_records,
    load_wallet_card_records,
    remove_cjk_latin_spaces,
    save_wallet_card_records,
)


router = APIRouter(tags=["wallet-cards"])

SCHEME_OPTIONS_FILE = WALLET_CARDS_FILE.with_name("wallet_card_options.json")
DEFAULT_SCHEMES = ["Visa", "Mastercard", "UnionPay", "American Express", "其他"]

def load_scheme_options():
    return load_json(SCHEME_OPTIONS_FILE, {"schemes": DEFAULT_SCHEMES}).get("schemes", DEFAULT_SCHEMES)

@router.get("/api/wallet-card-options")
def get_wallet_options():
    return {"schemes": load_scheme_options()}

@router.post("/api/wallet-card-options")
async def set_wallet_options(request: Request):
    payload = await request.json()
    values = payload.get("schemes") if isinstance(payload, dict) else None
    if not isinstance(values, list) or not values or len(values) > 50 or any(not isinstance(v, str) or not v.strip() or len(v.strip()) > 50 for v in values):
        return JSONResponse({"message": "请保留至少一个有效选项，每项不超过50字。"}, status_code=400)
    values = list(dict.fromkeys(v.strip() for v in values))
    save_json_atomic(SCHEME_OPTIONS_FILE, {"schemes": values})
    return {"schemes": values}


COVER_STYLES = {"standard", "decard-pink", "etherfi-prism", "plasma-dark", "plasma-light", "pokepay-green", "prepaid-green", "krak-red", "kraken-black", "coinbase-blue", "blackcat-photo", "payfun-gold", "dtcpay-gold", "starryblu-night", "mexc-black", "bunq-cloud", "yonder-dark", "virtual-orange", "mexc-global", "zopa-sage", "gmgn-green", "lava-black", "savo-green", "lloyds-green", "digitap-green", "trading212-black", "trading212-virtual-black", "sumup-pink", "gate-dark", "avalanche-red", "peanut-pink", "redotpay-dark", "tria-prism", "kolo-cypherpunk", "metamask-orange", "maya-purple"}


BRAND_ICONS = {103: 'decard.ico', 105: 'etherfi.png', 89: 'plasma.ico', 80: 'pokepay.png', 122: 'uu.ico', 24: 'krak.png', 23: 'krak.png', 158: 'krak.png', 91: 'blackcat.png', 83: 'skrill.ico', 93: 'payfun.svg', 79: 'dtcpay.ico', 69: 'starryblu.png', 99: 'mexc.png', 67: 'bunq.png', 45: 'yonder.png', 53: 'altery.png', 128: 'zopa.ico', 130: 'gmgn.png', 66: 'lava.png', 10: 'savo.png', 129: 'lloyds.png', 48: 'coinbase.svg', 12: 'digitap.ico', 56: 'trading212.svg', 68: 'sumup.svg', 154: 'gate.png', 136: 'avalanche.svg', 121: 'peanut.ico', 135: 'redotpay.svg', 131: 'tria.ico', 160: 'kolo.svg', 47: 'metamask.svg', 85: 'maya.png'}

def _brand_icon(record: dict) -> str:
    return "/static/images/wallet-brands/" + BRAND_ICONS.get(int(record.get("source_tool_id") or 0), "card.svg")


def _clean_text(value: str) -> str:
    return remove_cjk_latin_spaces((value or "").strip())


def _normalize_card_number(value: str) -> str:
    return re.sub(r"[\s-]", "", value or "")


def _format_card_number(value: str) -> str:
    number = _normalize_card_number(value)
    return " ".join(number[index:index + 4] for index in range(0, len(number), 4))


def _mask_card_number(value: str) -> str:
    number = _normalize_card_number(value)
    if len(number) < 4:
        return "•••• •••• •••• ••••"
    return f"•••• •••• •••• {number[-4:]}"


def _normalize_expiry(value: str) -> str:
    expiry = (value or "").strip()
    match = re.fullmatch(r"(0[1-9]|1[0-2])\s*/\s*(\d{2}|\d{4})", expiry)
    if not match:
        return ""
    year = match.group(2)[-2:]
    return f"{match.group(1)}/{year}"


def _validate_card_input(card_number: str, expiry: str, cvc: str) -> str | None:
    if not re.fullmatch(r"\d{12,19}", card_number):
        return "卡号需填写12至19位数字。"
    if not expiry:
        return "有效期格式应为MM/YY，例如08/29。"
    if not re.fullmatch(r"\d{3,4}", cvc):
        return "CVC安全码需填写3至4位数字。"
    return None


def _page_card(record: dict) -> dict:
    cover_style = str(record.get("cover_style") or "standard")
    bin_info = get_card_bin_info(str(record.get("card_number") or ""))
    return {
        "id": int(record.get("id", 0)),
        "name": record.get("name") or "未命名卡片",
        "software": record.get("software") or "--",
        "brand_icon": _brand_icon(record),
        "expiry_alert": card_expiry_status(record.get("expiry")),
        "scheme": record.get("scheme") or "CARD",
        "expiry": record.get("expiry") or "--/--",
        "card_variant": record.get("card_variant") or "",
        "cover_style": cover_style if cover_style in COVER_STYLES else "standard",
        "card_number_masked": _mask_card_number(str(record.get("card_number") or "")),
        "bin_country": bin_info["country"],
        "bin_alpha2": bin_info["alpha2"],
        "bin_flag": bin_info["flag"],
        "bin_badge": bin_info["badge"],
        "bin_issuer": bin_info["issuer"],
    }


def _detail_card(record: dict, source_tool: dict | None = None) -> dict:
    tool = source_tool or {}
    cover_style = str(record.get("cover_style") or "standard")
    bin_info = get_card_bin_info(str(record.get("card_number") or ""))
    return {
        "id": int(record.get("id", 0)),
        "name": record.get("name") or "",
        "software": record.get("software") or "",
        "brand_icon": _brand_icon(record),
        "scheme": record.get("scheme") or "其他",
        "card_variant": record.get("card_variant") or "",
        "cover_style": cover_style if cover_style in COVER_STYLES else "standard",
        "card_number": _format_card_number(str(record.get("card_number") or "")),
        "expiry": record.get("expiry") or "",
        "cvc": record.get("cvc") or "",
        "holder_name": record.get("holder_name") or "",
        "billing_address": record.get("billing_address") or "",
        "note": record.get("note") or "",
        "source_tool_id": int(record.get("source_tool_id") or 0),
        "country": tool.get("country") or "",
        "phone": tool.get("phone") or "",
        "login_method": tool.get("login_method") or "",
        "account_provider": tool.get("account_provider") or "",
        "kyc_provider": tool.get("kyc_provider") or "",
        "bin_country": bin_info["country"],
        "bin_alpha2": bin_info["alpha2"],
        "bin_flag": bin_info["flag"],
        "bin_issuer": bin_info["issuer"],
        "bin_info_display": bin_info["display"],
    }


@router.get("/wallet-cards", response_class=HTMLResponse)
def list_wallet_cards(request: Request, notice: str | None = None, error: str | None = None):
    records = sorted(
        load_wallet_card_records(),
        key=lambda card: int(card.get("id", 0)),
        reverse=True,
    )
    tool_options = sorted(
        load_card_records(),
        key=lambda tool: (str(tool.get("name") or "").casefold(), int(tool.get("id", 0))),
    )
    return request.app.state.templates.TemplateResponse(
        "wallet_cards.html",
        {
            "request": request,
            "active_page": "wallet-cards",
            "page_title": "境外卡",
            "wallet_cards": [_page_card(record) for record in records],
            "tool_options": tool_options,
            "scheme_options": load_scheme_options(),
            "notice": notice,
            "error": error,
        },
    )


@router.get("/api/wallet-cards/{card_id}", response_class=JSONResponse)
def get_wallet_card(card_id: int):
    record = next(
        (card for card in load_wallet_card_records() if int(card.get("id", 0)) == card_id),
        None,
    )
    if record is None:
        return JSONResponse(
            {"status": "error", "message": "卡片不存在。"},
            status_code=404,
            headers={"Cache-Control": "no-store"},
        )
    source_tool_id = int(record.get("source_tool_id") or 0)
    source_tool = next(
        (tool for tool in load_card_records() if int(tool.get("id", 0)) == source_tool_id),
        None,
    )
    return JSONResponse(
        {"status": "success", "card": _detail_card(record, source_tool)},
        headers={"Cache-Control": "no-store"},
    )


@router.post("/wallet-cards/add")
def add_wallet_card(
    name: str = Form(...),
    software: str = Form(...),
    source_tool_id: int = Form(0),
    scheme: str = Form("其他"),
    card_variant: str = Form(""),
    cover_style: str = Form("standard"),
    card_number: str = Form(...),
    expiry: str = Form(...),
    cvc: str = Form(...),
    holder_name: str = Form(...),
    billing_address: str = Form(...),
    note: str = Form(""),
):
    normalized_number = _normalize_card_number(card_number)
    normalized_expiry = _normalize_expiry(expiry)
    normalized_cvc = (cvc or "").strip()
    error = _validate_card_input(normalized_number, normalized_expiry, normalized_cvc)
    if error:
        return RedirectResponse(build_redirect_url("/wallet-cards", error=error), status_code=303)

    with json_file_transaction(WALLET_CARDS_FILE):
        records = load_wallet_card_records()
        next_id = max((int(card.get("id", 0)) for card in records), default=0) + 1
        records.append(
            {
                "id": next_id,
                "name": _clean_text(name),
                "software": _clean_text(software),
                "source_tool_id": source_tool_id,
                "scheme": scheme.strip() or "其他",
                "card_variant": _clean_text(card_variant),
                "cover_style": cover_style if cover_style in COVER_STYLES else "standard",
                "card_number": normalized_number,
                "expiry": normalized_expiry,
                "cvc": normalized_cvc,
                "holder_name": holder_name.strip(),
                "billing_address": billing_address.strip(),
                "note": _clean_text(note),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        save_wallet_card_records(records)
    return RedirectResponse(build_redirect_url("/wallet-cards", notice="境外卡片已添加。"), status_code=303)


@router.post("/wallet-cards/{card_id}/update")
def update_wallet_card(
    card_id: int,
    name: str = Form(...),
    software: str = Form(...),
    source_tool_id: int = Form(0),
    scheme: str = Form("其他"),
    card_variant: str = Form(""),
    cover_style: str = Form("standard"),
    card_number: str = Form(...),
    expiry: str = Form(...),
    cvc: str = Form(...),
    holder_name: str = Form(...),
    billing_address: str = Form(...),
    note: str = Form(""),
):
    normalized_number = _normalize_card_number(card_number)
    normalized_expiry = _normalize_expiry(expiry)
    normalized_cvc = (cvc or "").strip()
    error = _validate_card_input(normalized_number, normalized_expiry, normalized_cvc)
    if error:
        return RedirectResponse(build_redirect_url("/wallet-cards", error=error), status_code=303)

    found = False
    with json_file_transaction(WALLET_CARDS_FILE):
        records = load_wallet_card_records()
        for card in records:
            if int(card.get("id", 0)) == card_id:
                card.update(
                    name=_clean_text(name),
                    software=_clean_text(software),
                    source_tool_id=source_tool_id,
                    scheme=scheme.strip() or "其他",
                    card_variant=_clean_text(card_variant),
                    cover_style=cover_style if cover_style in COVER_STYLES else "standard",
                    card_number=normalized_number,
                    expiry=normalized_expiry,
                    cvc=normalized_cvc,
                    holder_name=holder_name.strip(),
                    billing_address=billing_address.strip(),
                    note=_clean_text(note),
                    updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                found = True
                break
        if found:
            save_wallet_card_records(records)

    message = "卡片信息已更新。" if found else "卡片不存在。"
    key = "notice" if found else "error"
    return RedirectResponse(build_redirect_url("/wallet-cards", **{key: message}), status_code=303)


@router.post("/wallet-cards/{card_id}/delete")
def delete_wallet_card(card_id: int):
    with json_file_transaction(WALLET_CARDS_FILE):
        records = load_wallet_card_records()
        kept = [card for card in records if int(card.get("id", 0)) != card_id]
        if len(kept) == len(records):
            return RedirectResponse(
                build_redirect_url("/wallet-cards", error="卡片不存在。"),
                status_code=303,
            )
        save_wallet_card_records(kept)
    return RedirectResponse(
        build_redirect_url("/wallet-cards", notice="境外卡片已删除。"),
        status_code=303,
    )
