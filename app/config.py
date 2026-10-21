from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# This desktop edition never shares writable storage with another checkout.
DATA_DIR = Path(os.getenv("FINBOARD_LOCAL_DATA_DIR", str(PROJECT_ROOT / "data"))).resolve()
if not DATA_DIR.is_relative_to(PROJECT_ROOT) or DATA_DIR == PROJECT_ROOT:
    raise RuntimeError("新版数据目录必须位于当前项目内部。")
DATABASE_PATH = DATA_DIR / "portfolio.db"
requested_database = os.getenv("DATABASE_URL", "")
if requested_database and requested_database != f"sqlite:///{DATABASE_PATH.as_posix()}":
    raise RuntimeError("新版禁止连接其他项目的数据库，请清除外部DATABASE_URL配置。")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "本地股票分析与持仓记录")
    host: str = "127.0.0.1"
    port: int = int(os.getenv("FINBOARD_LOCAL_PORT", "18011"))
    database_url: str = f"sqlite:///{DATABASE_PATH.as_posix()}"
    finnhub_api_key: str = os.getenv("FINNHUB_API_KEY", "").strip()
    twelve_data_api_key: str = os.getenv("TWELVEDATA_API_KEY", "").strip()
    quote_cache_seconds: int = int(os.getenv("QUOTE_CACHE_SECONDS", "10"))
    detail_cache_seconds: int = int(os.getenv("DETAIL_CACHE_SECONDS", "300"))
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "12"))
    detail_request_budget_seconds: float = float(
        os.getenv("DETAIL_REQUEST_BUDGET_SECONDS", "10.0")
    )
    portfolio_base_currency: str = (
        os.getenv("PORTFOLIO_BASE_CURRENCY", "CNY").strip().upper() or "CNY"
    )
    translate_news: bool = os.getenv("TRANSLATE_NEWS", "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model: str = (
        os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna"
    )
    x_bearer_token: str = os.getenv("X_BEARER_TOKEN", "").strip()
    proxy: str = (
        os.getenv("PROXY", "").strip()
        or os.getenv("http_proxy", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
