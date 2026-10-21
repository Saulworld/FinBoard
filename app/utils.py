from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from .config import PROJECT_ROOT, DATA_DIR
from .json_store import json_file_transaction, load_json, save_json_atomic, update_json

MARKET_LABELS = {
    "US": "美股",
    "ETF": "ETF",
    "HK": "港股",
    "CN": "A股",
}

CARDS_FILE = DATA_DIR / "cards.json"
CARD_OPTIONS_FILE = DATA_DIR / "card_options.json"
CARD_NOTICES_FILE = DATA_DIR / "card_notices.json"
WALLET_CARDS_FILE = DATA_DIR / "wallet_cards.json"
PHONES_FILE = DATA_DIR / "phones.json"
PHONE_OPTIONS_FILE = DATA_DIR / "phone_options.json"


def format_market_label(market: str | None) -> str:
    normalized = normalize_market(market)
    return MARKET_LABELS.get(normalized, normalized)


def get_preferred_providers(request) -> dict[str, str]:
    global_pref = request.cookies.get("glass_preferred_provider") or "auto"
    us_pref = request.cookies.get("glass_preferred_provider_us") or global_pref
    return {
        "US": us_pref,
        "ETF": us_pref,
        "CN": request.cookies.get("glass_preferred_provider_cn") or global_pref,
        "HK": request.cookies.get("glass_preferred_provider_hk") or global_pref,
    }


def register_jinja_globals(environment) -> None:
    from .config import get_settings

    settings = get_settings()
    environment.globals.update(
        format_money=format_money,
        format_percent=format_percent,
        format_datetime=format_datetime,
        get_market_currency=get_market_currency,
        market_labels=MARKET_LABELS,
        market_examples={key: market_example(key) for key in MARKET_LABELS},
        provider_status={
            "yahoo": "默认启用",
            "twelve_data": "已配置" if settings.twelve_data_api_key else "未配置",
            "finnhub": "已配置" if settings.finnhub_api_key else "未配置",
        },
        pref_us="auto",
        pref_cn="auto",
        pref_hk="auto",
        today_date=datetime.now().strftime("%Y-%m-%d"),
    )


def normalize_market(value: str | None) -> str:
    market = (value or "US").strip().upper()
    if market in {"A", "ASHARE", "CN", "SZ", "SS"}:
        return "CN"
    if market in {"HK", "HKS"}:
        return "HK"
    if market in {"ETF"}:
        return "ETF"
    return "US"


def normalize_symbol(value: str, market: str = "US") -> str:
    symbol = (value or "").strip().upper()
    market = normalize_market(market)
    if not symbol:
        return ""

    if market == "CN":
        if "." in symbol:
            return symbol
        code = "".join(ch for ch in symbol if ch.isdigit())
        if len(code) == 6:
            suffix = "SS" if code.startswith(("5", "6", "9")) else "SZ"
            return f"{code}.{suffix}"
        return symbol

    if market == "HK":
        if "." in symbol:
            return symbol
        code = "".join(ch for ch in symbol if ch.isdigit())
        if code:
            return f"{code.zfill(4)}.HK"
        return symbol

    return symbol


def market_example(market: str) -> str:
    examples = {
        "US": "AAPL / MSFT / NVDA / TSLA / AMZN / GOOGL / META",
        "ETF": "SPY / QQQ / VOO / DIA / IWM / ARKK",
        "HK": "0700 / 9988 / 1810 / 3690 / 9618 / 9888",
        "CN": "600519 / 000858 / 300750 / 601318 / 600036 / 600900",
    }
    return examples.get(
        normalize_market(market), "AAPL / MSFT / NVDA / TSLA / AMZN / GOOGL / META"
    )


def safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_market_currency(market: str | None) -> str:
    m = normalize_market(market)
    if m == "CN":
        return "CNY"
    elif m == "HK":
        return "HKD"
    else:
        return "USD"


def get_currency_symbol(currency: str | None) -> str:
    if not currency:
        return ""
    currency_upper = currency.upper()
    if currency_upper in ("USD", "$"):
        return "$"
    if currency_upper in ("CNY", "RMB", "¥", "￥"):
        return "¥"
    if currency_upper in ("HKD", "HK$"):
        return "HK$"
    return currency


def format_money(
    value: float | None, currency: str | None = None, digits: int = 2
) -> str:
    if value is None:
        return "--"
    symbol = get_currency_symbol(currency)
    is_negative = value < 0
    abs_value = abs(value)
    sign = "-" if is_negative else ""
    if symbol in ("$", "¥", "HK$"):
        return f"{sign}{symbol}{abs_value:,.{digits}f}"
    elif symbol:
        return f"{sign}{symbol} {abs_value:,.{digits}f}"
    return f"{sign}{abs_value:,.{digits}f}"


def format_percent(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "--"
    return f"{value:.{digits}f}%"


def format_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "--"
    return f"{value:,.{digits}f}"


def format_large_number(value: float | None, currency: str | None = None) -> str:
    if value is None:
        return "--"
    is_negative = value < 0
    absolute = abs(value)
    suffix = ""
    scaled = absolute
    if absolute >= 1_000_000_000_000:
        scaled = absolute / 1_000_000_000_000
        suffix = "T"
    elif absolute >= 1_000_000_000:
        scaled = absolute / 1_000_000_000
        suffix = "B"
    elif absolute >= 1_000_000:
        scaled = absolute / 1_000_000
        suffix = "M"
    elif absolute >= 1_000:
        scaled = absolute / 1_000
        suffix = "K"

    sign = "-" if is_negative else ""
    symbol = get_currency_symbol(currency)
    if symbol in ("$", "¥", "HK$"):
        return f"{sign}{symbol}{scaled:,.2f}{suffix}"
    elif symbol:
        return f"{sign}{symbol} {scaled:,.2f}{suffix}"
    return f"{sign}{scaled:,.2f}{suffix}"


def format_datetime(value: datetime | None) -> str:
    if not value:
        return "--"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone()
    return local.strftime("%Y-%m-%d %H:%M")


def calculate_phone_status(
    expiry_date: str | None, duration_days: Any = None
) -> dict[str, Any]:
    """Return a stable expiry status used by the dashboard and phone page."""
    if not expiry_date:
        return {"status": "normal", "days_remaining": None, "status_label": ""}
    try:
        expiry = datetime.strptime(str(expiry_date), "%Y-%m-%d").date()
    except ValueError:
        return {"status": "normal", "days_remaining": None, "status_label": ""}
    days_remaining = (expiry - datetime.now().date()).days
    if days_remaining < 0:
        return {
            "status": "expired",
            "days_remaining": days_remaining,
            "status_label": "已过期",
        }
    if days_remaining <= 15:
        return {
            "status": "expiring_soon",
            "days_remaining": days_remaining,
            "status_label": "临期",
        }
    return {"status": "normal", "days_remaining": days_remaining, "status_label": ""}


def build_redirect_url(path: str, **params: str | None) -> str:
    payload = {key: value for key, value in params.items() if value}
    if not payload:
        return path
    return f"{path}?{urlencode(payload)}"


def parse_holdings_text(
    text: str, default_market: str = "US"
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    default_market = normalize_market(default_market)

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [
            part.strip() for part in line.replace("|", ",").replace(";", ",").split(",")
        ]
        if len(parts) == 1:
            parts = [part.strip() for part in line.split("\t")]
        parts = [part for part in parts if part != ""]
        if not parts:
            continue

        header = parts[0].lower()
        if header in {"symbol", "ticker", "代码"}:
            continue

        if len(parts) < 3:
            errors.append(f"第 {line_number} 行列数不足，至少需要代码、数量、成本价。")
            continue

        input_symbol = parts[0]
        quantity = safe_float(parts[1])
        average_cost = safe_float(parts[2])
        market = normalize_market(parts[3] if len(parts) >= 4 else default_market)
        name = parts[4] if len(parts) >= 5 else ""
        note = parts[5] if len(parts) >= 6 else ""

        if quantity is None or average_cost is None:
            errors.append(f"第 {line_number} 行数量或成本价不是数字。")
            continue

        rows.append(
            {
                "input_symbol": input_symbol,
                "symbol": normalize_symbol(input_symbol, market),
                "market": market,
                "name": name,
                "quantity": quantity,
                "average_cost": average_cost,
                "note": note,
            }
        )

    return rows, errors


_translation_client = None


def _get_translation_client():
    global _translation_client
    if _translation_client is None:
        from .config import get_settings

        settings = get_settings()
        proxy = settings.proxy if settings.proxy else None
        _translation_client = httpx.Client(timeout=4.0, proxy=proxy)
    return _translation_client


def translate_text(text: str, target_lang: str = "zh-CN") -> str:
    if not text or not text.strip():
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": target_lang,
            "dt": "t",
            "q": text,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = _get_translation_client().get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        translated_segments = []
        if data and len(data) > 0 and data[0]:
            for segment in data[0]:
                if segment and len(segment) > 0:
                    translated_segments.append(segment[0])
        return "".join(translated_segments)
    except Exception:
        return text


def load_card_records() -> list[dict[str, Any]]:
    if not CARDS_FILE.exists():
        return []
    data = load_json(CARDS_FILE, [])
    for card in data:
        card.setdefault("color", "")
        card.setdefault("account_provider", "--")
    return data


def save_card_records(records: list[dict[str, Any]]) -> None:
    save_json_atomic(CARDS_FILE, records)


def load_card_notice_records() -> list[dict[str, Any]]:
    return load_json(CARD_NOTICES_FILE, [])


def save_card_notice_records(records: list[dict[str, Any]]) -> None:
    save_json_atomic(CARD_NOTICES_FILE, records)


def load_wallet_card_records() -> list[dict[str, Any]]:
    """Load the user's payment-card records without exposing them elsewhere."""
    return load_json(WALLET_CARDS_FILE, [])


def save_wallet_card_records(records: list[dict[str, Any]]) -> None:
    save_json_atomic(WALLET_CARDS_FILE, records)


def load_card_options() -> dict:
    default_options = {
        "kyc_methods": ["CNID", "CN护照"],
        "types": [
            "U卡",
            "虚拟卡",
            "银行",
            "交易所",
            "加密钱包",
            "支付钱包",
            "汇款",
            "券商",
            "电话卡",
            "IP购买",
            "浏览器模拟",
            "支付",
            "钱包",
            "电话",
            "税号",
            "金融软件",
            "私募交易",
        ],
        "countries": [
            "中国",
            "中国香港",
            "英国",
            "德国",
            "爱沙尼亚",
            "美国",
            "菲律宾",
            "日本",
            "奥地利",
        ],
        "login_methods": ["未绑定", "--"],
        "phones": ["--"],
        "account_providers": ["Lead Bank", "--"],
        "colors": [
            {"name": "红色", "value": "#fff5f5"},
            {"name": "黄色", "value": "#fefbeb"},
            {"name": "绿色", "value": "#f0fdf4"},
            {"name": "蓝色", "value": "#eff6ff"},
        ],
    }
    if not CARD_OPTIONS_FILE.exists():
        return default_options
    data = load_json(CARD_OPTIONS_FILE, dict(default_options))
    updated = False
    for key, value in default_options.items():
        if key not in data:
            data[key] = value
            updated = True
    return data


def save_card_options(options: dict[str, list[str]]) -> None:
    save_json_atomic(CARD_OPTIONS_FILE, options)


def load_phone_options() -> dict:
    default_options = {
        "countries": ["德国", "英国", "爱沙尼亚", "美国", "菲律宾", "中国"],
        "durations": [
            {"name": "1个月", "days": 30},
            {"name": "2个月", "days": 60},
            {"name": "3个月", "days": 90},
            {"name": "4个月", "days": 120},
            {"name": "6个月", "days": 180},
            {"name": "12个月 / 1年", "days": 360},
        ],
        "phones": ["--"],
    }
    if not PHONE_OPTIONS_FILE.exists():
        return default_options
    data = load_json(PHONE_OPTIONS_FILE, dict(default_options))
    updated = False
    for key, value in default_options.items():
        if key not in data:
            data[key] = value
            updated = True
    return data


def save_phone_options(options: dict[str, list[str]]) -> None:
    save_json_atomic(PHONE_OPTIONS_FILE, options)


def remove_cjk_latin_spaces(text: str) -> str:
    if not text:
        return text
    import re

    # Pattern 1: Chinese char followed by space followed by English letter/digit/parenthesis
    text = re.sub(r"([\u4e00-\u9fa5])\s+([a-zA-Z0-9\(\)\[\]])", r"\1\2", text)
    # Pattern 2: English/Digit/parenthesis followed by space followed by Chinese char
    text = re.sub(r"([a-zA-Z0-9\(\)\[\]])\s+([\u4e00-\u9fa5])", r"\1\2", text)
    return text


def capitalize_english(text: str) -> str:
    if not text:
        return text
    if "@" in text:
        return text
    import re

    return re.sub(r"[a-zA-Z]+", lambda m: m.group(0)[0].upper() + m.group(0)[1:], text)


def load_phone_records() -> list[dict]:
    return load_json(PHONES_FILE, [])


def save_phone_records(records: list[dict]) -> None:
    save_json_atomic(PHONES_FILE, records)
