from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.json_store import json_file_transaction
from app.utils import (
    PHONES_FILE,
    build_redirect_url,
    load_phone_options,
    load_phone_records,
    remove_cjk_latin_spaces,
    save_phone_options,
    save_phone_records,
)


router = APIRouter(tags=["phones"])


@router.get("/phones", response_class=HTMLResponse)
def list_phones(request: Request, notice: str | None = None, error: str | None = None):
    return request.app.state.templates.TemplateResponse(
        "phones.html",
        {
            "request": request, "active_page": "phones", "page_title": "境外号码",
            "phones": load_phone_records(), "options": load_phone_options(),
            "notice": notice, "error": error,
        },
    )


@router.post("/phones/add")
def add_phone(
    name: str = Form(...), phone: str = Form(...), country: str = Form(...),
    status: str = Form("已激活"), last_recharge_date: str = Form(""),
    expiry_date: str = Form(""), renewal_method: str = Form(""), note: str = Form(""),
):
    with json_file_transaction(PHONES_FILE):
        phones = load_phone_records()
        next_id = max((int(item.get("id", 0)) for item in phones), default=0) + 1
        phones.append(
            {
                "id": next_id, "name": remove_cjk_latin_spaces(name.strip()), "phone": phone.strip(),
                "country": remove_cjk_latin_spaces(country.strip()), "status": status.strip(),
                "last_recharge_date": last_recharge_date, "expiry_date": expiry_date,
                "renewal_method": remove_cjk_latin_spaces(renewal_method.strip()),
                "note": remove_cjk_latin_spaces(note.strip()),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        save_phone_records(phones)
    return RedirectResponse(build_redirect_url("/phones", notice="境外号码已添加。"), status_code=303)


@router.post("/phones/{phone_id}/update", response_class=JSONResponse)
def update_phone(
    phone_id: int, name: str = Form(...), phone: str = Form(...), country: str = Form(...),
    status: str = Form("已激活"), last_recharge_date: str = Form(""),
    expiry_date: str = Form(""), renewal_method: str = Form(""), note: str = Form(""),
):
    found = False
    with json_file_transaction(PHONES_FILE):
        phones = load_phone_records()
        for item in phones:
            if int(item.get("id", 0)) == phone_id:
                item.update(
                    name=remove_cjk_latin_spaces(name.strip()), phone=phone.strip(),
                    country=remove_cjk_latin_spaces(country.strip()), status=status.strip(),
                    last_recharge_date=last_recharge_date, expiry_date=expiry_date,
                    renewal_method=remove_cjk_latin_spaces(renewal_method.strip()),
                    note=remove_cjk_latin_spaces(note.strip()),
                )
                found = True
                break
        if found:
            save_phone_records(phones)
    return JSONResponse({"status": "success"} if found else {"status": "error", "message": "记录不存在"}, status_code=200 if found else 404)


@router.post("/phones/{phone_id}/delete", response_class=JSONResponse)
def delete_phone(phone_id: int):
    with json_file_transaction(PHONES_FILE):
        phones = load_phone_records()
        kept = [item for item in phones if int(item.get("id", 0)) != phone_id]
        if len(kept) == len(phones):
            return JSONResponse({"status": "error", "message": "记录不存在"}, status_code=404)
        save_phone_records(kept)
    return JSONResponse({"status": "success"})


@router.get("/api/phones/options", response_class=JSONResponse)
def get_phone_options():
    return JSONResponse(load_phone_options())


@router.post("/api/phones/options", response_class=JSONResponse)
async def set_phone_options(request: Request):
    save_phone_options(await request.json())
    return JSONResponse({"status": "success"})
