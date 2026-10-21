"""Private local register of overseas identity documents and tax identifiers."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import DATA_DIR
from app.json_store import json_file_transaction, load_json, save_json_atomic
from app.utils import build_redirect_url, remove_cjk_latin_spaces


router = APIRouter(tags=["overseas-documents"])
DOCUMENTS_FILE = DATA_DIR / "overseas_documents.json"
OPTIONS_FILE = DATA_DIR / "overseas_document_options.json"
DEFAULT_DOCUMENT_TYPES = ["身份证", "护照", "税号(TIN)", "税务识别号", "居留许可", "驾驶证", "社会保障号码", "其他"]
ADDRESS_OPTIONS = []


def _load() -> list[dict]:
    records = load_json(DOCUMENTS_FILE, [])
    if not isinstance(records, list):
        raise RuntimeError("境外证件数据格式异常，已停止操作以保护原有数据。")
    return records


def _load_document_options() -> dict:
    options = load_json(OPTIONS_FILE, {"document_types": DEFAULT_DOCUMENT_TYPES})
    if not isinstance(options, dict):
        raise RuntimeError("证件选项格式异常，已停止操作以保护原有数据。")
    options = dict(options)
    if "countries" not in options:
        options["countries"] = list(dict.fromkeys([item.get("country") for item in _load() if item.get("country")] + ["中国", "菲律宾", "马来西亚", "美国", "英国"]))
    for key in ("document_types", "countries"):
        values = options.get(key)
        if not isinstance(values, list) or not values or any(not isinstance(value, str) for value in values):
            raise RuntimeError("证件选项格式异常，已停止操作以保护原有数据。")
    return options


def _load_document_types() -> list[str]:
    return _load_document_options()["document_types"]


@router.get("/api/overseas-document-options")
def get_document_options():
    return JSONResponse(_load_document_options(), headers={"Cache-Control": "no-store"})


@router.post("/api/overseas-document-options")
async def save_document_options(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict) or not any(key in payload for key in ("document_types", "countries")):
        return JSONResponse({"message": "请提交证件类型或国家/地区选项。"}, status_code=400)
    changes = {}
    for key in ("document_types", "countries"):
        if key not in payload:
            continue
        values = payload[key]
        if (not isinstance(values, list) or not 1 <= len(values) <= 50 or
                any(not isinstance(value, str) or not value.strip() or len(value.strip()) > 80 for value in values)):
            return JSONResponse({"message": "每类请保留至少一个选项，每项不超过80字。"}, status_code=400)
        changes[key] = list(dict.fromkeys(_clean(value) for value in values))
    with json_file_transaction(OPTIONS_FILE):
        options = _load_document_options()
        options.update(changes)
        save_json_atomic(OPTIONS_FILE, options)
    return JSONResponse(options, headers={"Cache-Control": "no-store"})


def _clean(value: str) -> str:
    return remove_cjk_latin_spaces((value or "").strip())


def _flag_theme(country: str) -> str:
    """Use the country of the record for its cover, regardless of document type."""
    normalized = (country or "").strip().casefold()
    if normalized in {"中国", "中国大陆", "中华人民共和国", "china", "prc"}:
        return "china"
    if normalized in {"菲律宾", "philippines", "ph"}:
        return "philippines"
    if normalized in {"马来西亚", "malaysia", "my"}:
        return "malaysia"
    return "standard"


def _default_address(country: str) -> str:
    normalized = (country or "").strip().casefold()
    aliases = {"philippines": "菲律宾", "ph": "菲律宾", "malaysia": "马来西亚", "my": "马来西亚"}
    name = aliases.get(normalized, normalized)
    return next((item["address"] for item in ADDRESS_OPTIONS if item["country"] == name), "")


def _fields(country: str, document_type: str, number: str, holder: str,
            issued_on: str, expires_on: str, issuer: str, address: str, note: str) -> tuple[dict, str | None]:
    fields = {
        "country": _clean(country), "document_type": _clean(document_type),
        "number": (number or "").strip(), "holder": _clean(holder),
        "issued_on": issued_on.strip(), "expires_on": expires_on.strip(),
        "issuer": _clean(issuer), "address": _clean(address), "note": _clean(note),
    }
    if not all(fields[key] for key in ("country", "document_type", "number")):
        return fields, "国家/地区、证件类型和证件号不能为空。"
    limits = {"country": 80, "document_type": 80, "number": 100, "holder": 100,
              "issuer": 150, "address": 300, "note": 500}
    if any(len(fields[key]) > limit for key, limit in limits.items()):
        return fields, "输入内容过长，请缩短后重试。"
    parsed = {}
    for key in ("issued_on", "expires_on"):
        if fields[key]:
            try:
                parsed[key] = date.fromisoformat(fields[key])
                if parsed[key].isoformat() != fields[key]:
                    raise ValueError
            except ValueError:
                return fields, "日期格式应为YYYY-MM-DD。"
    if parsed.get("issued_on") and parsed.get("expires_on") and parsed["expires_on"] < parsed["issued_on"]:
        return fields, "到期日期不能早于签发日期。"
    return fields, None


def _public(record: dict) -> dict:
    number = str(record.get("number") or "")
    visible = number[-4:] if len(number) > 4 else ""
    result = {key: record.get(key, "") for key in
              ("id", "country", "document_type", "holder", "issued_on", "expires_on", "issuer")}
    result["masked_number"] = f"•••• {visible}" if visible else "••••"
    result["flag_theme"] = _flag_theme(str(record.get("country") or ""))
    expiry = record.get("expires_on") or ""
    result["expiry_status"] = "none"
    if expiry:
        try:
            expires = date.fromisoformat(expiry)
            result["expiry_status"] = "expired" if expires < date.today() else (
                "soon" if expires <= date.today() + timedelta(days=30) else "valid"
            )
        except ValueError:
            pass
    return result


@router.get("/overseas-documents", response_class=HTMLResponse)
def list_documents(request: Request, notice: str | None = None, error: str | None = None):
    records = [_public(item) for item in _load()]
    countries: dict[str, dict] = {}
    for item in records:
        name = item["country"]
        if name not in countries:
            countries[name] = {"name": name, "total": 0, "types": {}}
        countries[name]["total"] += 1
        type_name = item["document_type"]
        label = "税号" if type_name == "税号(TIN)" else type_name
        countries[name]["types"][label] = countries[name]["types"].get(label, 0) + 1
    return request.app.state.templates.TemplateResponse(
        "overseas_documents.html",
        {"request": request, "active_page": "overseas-documents", "page_title": "境外证件",
         "documents": records, "countries": list(countries.values()),
         "document_types": _load_document_types(), "country_options": _load_document_options()["countries"], "address_options": ADDRESS_OPTIONS,
         "notice": notice, "error": error},
    )


@router.post("/overseas-documents/add")
def add_document(country: str = Form(""), document_type: str = Form(""),
                 number: str = Form(""), holder: str = Form(""),
                 issued_on: str = Form(""), expires_on: str = Form(""),
                 issuer: str = Form(""), address: str = Form(""), note: str = Form("")):
    fields, error = _fields(country, document_type, number, holder, issued_on, expires_on, issuer, address, note)
    if error:
        return RedirectResponse(build_redirect_url("/overseas-documents", error=error), status_code=303)
    if not fields["address"]:
        fields["address"] = _default_address(fields["country"])
    with json_file_transaction(DOCUMENTS_FILE):
        records = _load()
        fields.update(id=max((int(item.get("id", 0)) for item in records), default=0) + 1,
                      created_at=datetime.now().isoformat(timespec="seconds"))
        records.append(fields)
        save_json_atomic(DOCUMENTS_FILE, records)
    return RedirectResponse(build_redirect_url("/overseas-documents", notice="境外证件已添加。"), status_code=303)


@router.get("/api/overseas-documents/{document_id}")
def document_detail(document_id: int):
    for item in _load():
        if int(item.get("id", 0)) == document_id:
            return JSONResponse({"document": item}, headers={"Cache-Control": "no-store"})
    return JSONResponse({"message": "记录不存在。"}, status_code=404)


@router.post("/overseas-documents/{document_id}/update")
def update_document(document_id: int, country: str = Form(""), document_type: str = Form(""),
                    number: str = Form(""), holder: str = Form(""),
                    issued_on: str = Form(""), expires_on: str = Form(""),
                    issuer: str = Form(""), address: str | None = Form(None), note: str = Form("")):
    fields, error = _fields(country, document_type, number, holder, issued_on, expires_on, issuer, address or "", note)
    if error:
        return JSONResponse({"message": error}, status_code=400)
    with json_file_transaction(DOCUMENTS_FILE):
        records = _load()
        for item in records:
            if int(item.get("id", 0)) == document_id:
                if address is None:
                    fields["address"] = item.get("address", "")
                item.update(fields, updated_at=datetime.now().isoformat(timespec="seconds"))
                save_json_atomic(DOCUMENTS_FILE, records)
                return {"status": "success"}
    return JSONResponse({"message": "记录不存在。"}, status_code=404)


@router.post("/overseas-documents/{document_id}/delete")
def delete_document(document_id: int):
    with json_file_transaction(DOCUMENTS_FILE):
        records = _load()
        kept = [item for item in records if int(item.get("id", 0)) != document_id]
        if len(kept) == len(records):
            return JSONResponse({"message": "记录不存在。"}, status_code=404)
        save_json_atomic(DOCUMENTS_FILE, kept)
    return {"status": "success"}
