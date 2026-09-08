from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pandas as pd
import yfinance as yf

from .utils import normalize_market, safe_float


@dataclass
class QuoteData:
    symbol: str
    market: str
    price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    currency: str | None = None
    exchange: str | None = None
    source: str = ""
    updated_at: datetime | None = None
    market_state: str | None = None


@dataclass
class NewsItem:
    title: str
    source: str
    published_at: datetime | None
    url: str
    summary: str = ""


def _safe_call(factory, default):
    try:
        return factory()
    except Exception:
        return default


def _to_datetime_from_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    number = safe_float(value)
    if number is None:
        return None
    try:
        return datetime.fromtimestamp(number, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _latest_statement_value(frame: pd.DataFrame, candidates: list[str]) -> float | None:
    if frame is None or frame.empty:
        return None
    frame = frame.copy()
    frame.index = frame.index.astype(str)
    for candidate in candidates:
        if candidate not in frame.index:
            continue
        series = frame.loc[candidate].dropna()
        if series.empty:
            continue
        return safe_float(series.iloc[0])
    return None


class YahooFinanceProvider:
    source_name = "Yahoo Finance"

    def __init__(self) -> None:
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        from .config import get_settings
        settings = get_settings()
        if settings.proxy:
            self.session.proxies = {
                "http": settings.proxy,
                "https": settings.proxy
            }

    def _get_ticker(self, symbol: str) -> yf.Ticker:
        return yf.Ticker(symbol, session=self.session)

    def _fetch_single_quote(self, symbol: str, market: str) -> QuoteData:
        market = normalize_market(market)
        ticker = self._get_ticker(symbol)
        
        meta = None
        try:
            meta = ticker.history_metadata
        except Exception as e:
            print(f"Error fetching history_metadata for {symbol}: {e}")
            
        if meta:
            import time
            now = time.time()
            ctp = meta.get("currentTradingPeriod", {})
            pre = ctp.get("pre", {})
            reg = ctp.get("regular", {})
            post = ctp.get("post", {})
            
            pre_start = pre.get("start")
            pre_end = pre.get("end")
            reg_start = reg.get("start")
            reg_end = reg.get("end")
            post_start = post.get("start")
            post_end = post.get("end")
            
            market_state = None
            if pre_start and pre_end and pre_start <= now < pre_end:
                market_state = "PRE"
            elif post_start and post_end and post_start <= now < post_end:
                market_state = "POST"
            elif reg_start and reg_end and reg_start <= now < reg_end:
                market_state = "REGULAR"
                
            regular_price = safe_float(meta.get("regularMarketPrice"))
            previous_close = safe_float(meta.get("previousClose"))
            
            last_trade = meta.get("lastTrade") or {}
            last_price = safe_float(last_trade.get("Price"))
            
            price = None
            prev_close = None
            state_label = None
            
            if market_state in ("PRE", "POST") and last_price is not None:
                price = last_price
                prev_close = regular_price if regular_price is not None else previous_close
                state_label = market_state
            else:
                price = regular_price if regular_price is not None else last_price
                prev_close = previous_close
                state_label = None
                
            change = None
            change_percent = None
            if price is not None and prev_close not in (None, 0):
                change = price - prev_close
                change_percent = (change / prev_close) * 100
                
            return QuoteData(
                symbol=symbol,
                market=market,
                price=price,
                previous_close=prev_close,
                change=change,
                change_percent=change_percent,
                currency=meta.get("currency") or "USD",
                exchange=meta.get("exchangeName") or meta.get("fullExchangeName"),
                source=self.source_name,
                updated_at=datetime.now(timezone.utc),
                market_state=state_label,
            )
            
        # Fallback to fast_info if history_metadata failed
        fast_info = _safe_call(lambda: dict(ticker.fast_info), {})
        price = safe_float(fast_info.get("lastPrice") or fast_info.get("regularMarketPrice"))
        previous_close = safe_float(fast_info.get("previousClose") or fast_info.get("regularMarketPreviousClose"))
        change = None
        change_percent = None
        if price is not None and previous_close not in (None, 0):
            change = price - previous_close
            change_percent = (change / previous_close) * 100
            
        return QuoteData(
            symbol=symbol,
            market=market,
            price=price,
            previous_close=previous_close,
            change=change,
            change_percent=change_percent,
            currency=fast_info.get("currency") or "USD",
            exchange=fast_info.get("exchange"),
            source=self.source_name,
            updated_at=datetime.now(timezone.utc),
            market_state=None,
        )

    def get_quote(self, symbol: str, market: str) -> QuoteData:
        return self._fetch_single_quote(symbol, market)

    def get_quotes_batch(self, pairs: list[tuple[str, str]]) -> dict[tuple[str, str], QuoteData]:
        ordered_pairs = list(dict.fromkeys(pairs))
        us_pairs = [pair for pair in ordered_pairs if normalize_market(pair[1]) in {"US", "ETF"}]
        if not us_pairs:
            return {}
            
        from concurrent.futures import ThreadPoolExecutor
        def _fetch_one(pair):
            symbol, market = pair
            try:
                return pair, self._fetch_single_quote(symbol, market)
            except Exception as e:
                print(f"Error fetching real-time quote for {symbol}: {e}")
                return pair, QuoteData(
                    symbol=symbol,
                    market=normalize_market(market),
                    price=None,
                    previous_close=None,
                    change=None,
                    change_percent=None,
                    currency="USD",
                    source=self.source_name,
                    updated_at=datetime.now(timezone.utc),
                    market_state=None,
                )
                
        with ThreadPoolExecutor(max_workers=min(len(us_pairs), 15)) as executor:
            results = dict(executor.map(_fetch_one, us_pairs))
        return results

    def get_profile(self, symbol: str) -> dict[str, Any]:
        ticker = self._get_ticker(symbol)
        try:
            info = ticker.info
            if info:
                return info
        except Exception:
            pass
            
        fallback = {}
        try:
            meta = ticker.history_metadata or {}
            fallback.update({
                "symbol": symbol,
                "shortName": meta.get("shortName") or meta.get("longName") or symbol,
                "longName": meta.get("longName") or meta.get("shortName") or symbol,
                "currency": meta.get("currency") or "USD",
                "exchange": meta.get("exchangeName") or meta.get("fullExchangeName"),
            })
        except Exception:
            pass
            
        try:
            fast_info = dict(ticker.fast_info)
            fallback.update({
                "currency": fallback.get("currency") or fast_info.get("currency") or "USD",
                "exchange": fallback.get("exchange") or fast_info.get("exchange"),
                "regularMarketPreviousClose": fast_info.get("regularMarketPreviousClose") or fast_info.get("previousClose"),
                "regularMarketPrice": fast_info.get("lastPrice") or fast_info.get("regularMarketPrice"),
            })
        except Exception:
            pass
            
        return fallback

    def get_history(self, symbol: str, period: str = "1mo", interval: str = "1d") -> list[dict[str, Any]]:
        ticker = self._get_ticker(symbol)
        history = _safe_call(lambda: ticker.history(period=period, interval=interval, auto_adjust=False), pd.DataFrame())
        if history.empty:
            return []

        points: list[dict[str, Any]] = []
        for index, row in history.tail(60).iterrows():
            close_value = safe_float(row.get("Close"))
            if close_value is None:
                continue
            if hasattr(index, "to_pydatetime"):
                stamp = index.to_pydatetime()
            else:
                stamp = index
            points.append(
                {
                    "date": stamp.strftime("%Y-%m-%d"),
                    "close": close_value,
                }
            )
        return points

    def get_news(self, symbol: str, limit: int = 12) -> list[NewsItem]:
        ticker = self._get_ticker(symbol)
        raw_items = _safe_call(lambda: ticker.news or [], [])
        items: list[NewsItem] = []

        for item in raw_items[:limit]:
            payload = item.get("content") if isinstance(item, dict) and isinstance(item.get("content"), dict) else item
            title = payload.get("title") or item.get("title") or ""
            source = payload.get("provider", {}).get("displayName") if isinstance(payload.get("provider"), dict) else None
            source = source or payload.get("publisher") or item.get("publisher") or "Yahoo"
            url = payload.get("canonicalUrl", {}).get("url") if isinstance(payload.get("canonicalUrl"), dict) else None
            url = url or payload.get("link") or item.get("link") or ""
            summary = payload.get("summary") or item.get("summary") or ""
            published_at = _to_datetime_from_timestamp(
                payload.get("pubDate")
                or payload.get("providerPublishTime")
                or item.get("providerPublishTime")
            )
            if not title or not url:
                continue
            items.append(
                NewsItem(
                    title=title,
                    source=source,
                    published_at=published_at,
                    url=url,
                    summary=summary,
                )
            )
        return items

    def get_analyst_view(self, symbol: str, info: dict[str, Any] | None = None) -> dict[str, Any]:
        ticker = self._get_ticker(symbol)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_targets = executor.submit(lambda: ticker.analyst_price_targets)
            future_recommendations = executor.submit(lambda: ticker.recommendations_summary)
            targets = _safe_call(future_targets.result, {})
            recommendations = _safe_call(future_recommendations.result, None)
        info = info or {}
        breakdown: dict[str, int] = {}
        if recommendations is not None and hasattr(recommendations, "empty") and not recommendations.empty:
            row = recommendations.iloc[0].to_dict()
            for key, value in row.items():
                if str(key).lower() == "period":
                    continue
                number = safe_float(value)
                if number is not None:
                    breakdown[str(key)] = int(number)

        if not targets:
            targets = {
                "mean": info.get("targetMeanPrice"),
                "high": info.get("targetHighPrice"),
                "low": info.get("targetLowPrice"),
                "current": info.get("currentPrice"),
                "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
                "recommendationKey": info.get("recommendationKey"),
            }

        return {
            "price_targets": targets,
            "recommendation_breakdown": breakdown,
            "recommendation_key": info.get("recommendationKey"),
            "analyst_count": info.get("numberOfAnalystOpinions") or targets.get("numberOfAnalystOpinions"),
            "source": self.source_name,
        }

    def get_fundamentals(self, symbol: str, info: dict[str, Any] | None = None) -> dict[str, Any]:
        ticker = self._get_ticker(symbol)
        info = info or {}
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_income = executor.submit(lambda: ticker.quarterly_income_stmt)
            future_cashflow = executor.submit(lambda: ticker.quarterly_cashflow)
            future_balance = executor.submit(lambda: ticker.quarterly_balance_sheet)
            quarterly_income = _safe_call(future_income.result, pd.DataFrame())
            quarterly_cashflow = _safe_call(future_cashflow.result, pd.DataFrame())
            quarterly_balance = _safe_call(future_balance.result, pd.DataFrame())

        return {
            "info": info,
            "latest_quarter_revenue": _latest_statement_value(quarterly_income, ["Total Revenue", "Operating Revenue"]),
            "latest_quarter_net_income": _latest_statement_value(
                quarterly_income,
                ["Net Income", "Net Income Common Stockholders"],
            ),
            "latest_quarter_operating_cashflow": _latest_statement_value(
                quarterly_cashflow,
                ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
            ),
            "latest_cash": _latest_statement_value(quarterly_balance, ["Cash And Cash Equivalents", "Cash"]),
            "latest_total_debt": _latest_statement_value(
                quarterly_balance,
                ["Total Debt", "Long Term Debt And Capital Lease Obligation"],
            ),
            "source": self.source_name,
        }


class FinnhubProvider:
    source_name = "Finnhub"

    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        from .config import get_settings
        settings = get_settings()
        proxy = settings.proxy if settings.proxy else None
        self.client = httpx.Client(timeout=timeout_seconds, proxy=proxy)

    def available(self) -> bool:
        return bool(self.api_key)

    def _get(self, endpoint: str, params: dict[str, Any]) -> Any:
        if not self.available():
            return {}
        url = f"https://finnhub.io/api/v1{endpoint}"
        payload = dict(params)
        payload["token"] = self.api_key
        response = self.client.get(url, params=payload)
        response.raise_for_status()
        return response.json()

    def get_quote(self, symbol: str, market: str) -> QuoteData:
        payload = _safe_call(lambda: self._get("/quote", {"symbol": symbol}), {})
        price = safe_float(payload.get("c"))
        previous_close = safe_float(payload.get("pc"))
        change = safe_float(payload.get("d"))
        change_percent = safe_float(payload.get("dp"))
        return QuoteData(
            symbol=symbol,
            market=normalize_market(market),
            price=price,
            previous_close=previous_close,
            change=change,
            change_percent=change_percent,
            source=self.source_name,
            updated_at=_to_datetime_from_timestamp(payload.get("t")) or datetime.now(timezone.utc),
        )

    def get_news(self, symbol: str, limit: int = 12) -> list[NewsItem]:
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=30)
        payload = _safe_call(
            lambda: self._get(
                "/company-news",
                {
                    "symbol": symbol,
                    "from": start.isoformat(),
                    "to": today.isoformat(),
                },
            ),
            [],
        )
        items: list[NewsItem] = []
        for item in payload[:limit]:
            title = item.get("headline") or ""
            url = item.get("url") or ""
            if not title or not url:
                continue
            items.append(
                NewsItem(
                    title=title,
                    source=item.get("source") or self.source_name,
                    published_at=_to_datetime_from_timestamp(item.get("datetime")),
                    url=url,
                    summary=item.get("summary") or "",
                )
            )
        return items

    def get_consensus(self, symbol: str) -> dict[str, Any]:
        payload = _safe_call(lambda: self._get("/stock/recommendation", {"symbol": symbol}), [])
        if not payload:
            return {"price_targets": {}, "recommendation_breakdown": {}, "source": self.source_name}
        latest = sorted(payload, key=lambda item: item.get("period", ""), reverse=True)[0]
        breakdown = {
            "Strong Buy": latest.get("strongBuy", 0),
            "Buy": latest.get("buy", 0),
            "Hold": latest.get("hold", 0),
            "Sell": latest.get("sell", 0),
            "Strong Sell": latest.get("strongSell", 0),
        }
        total = sum(int(value or 0) for value in breakdown.values())
        weighted = None
        if total:
            weighted = (
                breakdown["Strong Buy"] * 1
                + breakdown["Buy"] * 2
                + breakdown["Hold"] * 3
                + breakdown["Sell"] * 4
                + breakdown["Strong Sell"] * 5
            ) / total
        return {
            "price_targets": {},
            "recommendation_breakdown": breakdown,
            "recommendation_mean": weighted,
            "analyst_count": total,
            "period": latest.get("period"),
            "source": self.source_name,
        }

    def get_basic_financials(self, symbol: str) -> dict[str, Any]:
        payload = _safe_call(lambda: self._get("/stock/metric", {"symbol": symbol, "metric": "all"}), {})
        return payload.get("metric", {}) if isinstance(payload, dict) else {}

    def get_profile(self, symbol: str) -> dict[str, Any]:
        payload = _safe_call(lambda: self._get("/stock/profile2", {"symbol": symbol}), {})
        return payload if isinstance(payload, dict) else {}


class TwelveDataProvider:
    source_name = "Twelve Data"

    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        from .config import get_settings
        settings = get_settings()
        proxy = settings.proxy if settings.proxy else None
        self.client = httpx.Client(timeout=timeout_seconds, proxy=proxy)

    def available(self) -> bool:
        return bool(self.api_key)

    def _get(self, endpoint: str, params: dict[str, Any]) -> Any:
        if not self.available():
            return {}
        url = f"https://api.twelvedata.com/{endpoint}"
        payload = dict(params)
        payload["apikey"] = self.api_key
        response = self.client.get(url, params=payload)
        response.raise_for_status()
        return response.json()

    def get_quote(self, symbol: str, market: str) -> QuoteData:
        payload = _safe_call(lambda: self._get("quote", {"symbol": symbol}), {})
        price = safe_float(payload.get("close") or payload.get("price"))
        previous_close = safe_float(payload.get("previous_close"))
        change = safe_float(payload.get("change"))
        change_percent = safe_float(payload.get("percent_change"))
        updated_at = None
        if payload.get("timestamp"):
            updated_at = _to_datetime_from_timestamp(payload.get("timestamp"))
        elif payload.get("datetime"):
            try:
                updated_at = datetime.fromisoformat(str(payload.get("datetime"))).replace(tzinfo=timezone.utc)
            except ValueError:
                updated_at = None
        return QuoteData(
            symbol=symbol,
            market=normalize_market(market),
            price=price,
            previous_close=previous_close,
            change=change,
            change_percent=change_percent,
            currency=payload.get("currency"),
            exchange=payload.get("exchange"),
            source=self.source_name,
            updated_at=updated_at or datetime.now(timezone.utc),
        )


def get_chinese_market_state(market: str) -> str | None:
    tz_beijing = timezone(timedelta(hours=8))
    now_beijing = datetime.now(tz_beijing)
    if now_beijing.weekday() >= 5:
        return None
    time_num = now_beijing.hour * 100 + now_beijing.minute
    if market == "CN":
        if 915 <= time_num < 930:
            return "PRE"
        elif 1500 <= time_num < 1530:
            return "POST"
    elif market == "HK":
        if 900 <= time_num < 930:
            return "PRE"
        elif 1600 <= time_num < 1610:
            return "POST"
    return None


class TencentFinanceProvider:
    source_name = "腾讯财经"

    def __init__(self) -> None:
        from .config import get_settings
        settings = get_settings()
        proxy = settings.proxy if settings.proxy else None
        self.client = httpx.Client(timeout=4.0, proxy=proxy)

    def get_quote(self, symbol: str, market: str) -> QuoteData:
        market = normalize_market(market)
        tencent_symbol = ""
        if market == "CN":
            parts = symbol.split(".")
            code = parts[0]
            suffix = parts[1] if len(parts) > 1 else ""
            if suffix == "SS":
                tencent_symbol = f"sh{code}"
            elif suffix == "SZ":
                tencent_symbol = f"sz{code}"
            else:
                tencent_symbol = f"sh{code}" if code.startswith(("5", "6", "9")) else f"sz{code}"
        elif market == "HK":
            code = symbol.split(".")[0].upper()
            if code in ("^HSI", "HSI"):
                tencent_symbol = "hkHSI"
            else:
                tencent_symbol = f"hk{code.zfill(5)}"
        elif market == "US":
            tencent_symbol = f"us{symbol.upper()}"
        else:
            raise ValueError("Tencent Finance only supports CN, HK and US markets")

        url = f"http://qt.gtimg.cn/q=s_{tencent_symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = self.client.get(url, headers=headers)
        response.raise_for_status()
        content = response.content.decode("gbk")

        if "=" in content:
            parts = content.split("=")[1].strip().strip('";').split("~")
            if len(parts) >= 6:
                price = safe_float(parts[3])
                change = safe_float(parts[4])
                change_percent = safe_float(parts[5])
                currency = "CNY" if market == "CN" else "HKD" if market == "HK" else "USD"
                market_state = get_chinese_market_state(market) if market in ("CN", "HK") else None
                return QuoteData(
                    symbol=symbol,
                    market=market,
                    price=price,
                    previous_close=price - change if price is not None and change is not None else None,
                    change=change,
                    change_percent=change_percent,
                    currency=currency,
                    exchange="SSE/SZSE" if market == "CN" else "HKEX" if market == "HK" else "US",
                    source=self.source_name,
                    updated_at=datetime.now(timezone.utc),
                    market_state=market_state,
                )
        raise ValueError("Failed to parse Tencent response")

    def get_quotes_batch(self, pairs: list[tuple[str, str]]) -> dict[tuple[str, str], QuoteData]:
        import re
        results = {}
        if not pairs:
            return results
            
        tencent_to_pair = {}
        tencent_symbols = []
        for symbol, market in pairs:
            market = normalize_market(market)
            if market == "CN":
                parts = symbol.split(".")
                code = parts[0]
                suffix = parts[1] if len(parts) > 1 else ""
                if suffix == "SS":
                    tencent_symbol = f"sh{code}"
                elif suffix == "SZ":
                    tencent_symbol = f"sz{code}"
                else:
                    tencent_symbol = f"sh{code}" if code.startswith(("5", "6", "9")) else f"sz{code}"
            elif market == "HK":
                code = symbol.split(".")[0].upper()
                if code in ("^HSI", "HSI"):
                    tencent_symbol = "hkHSI"
                else:
                    tencent_symbol = f"hk{code.zfill(5)}"
            elif market == "US":
                tencent_symbol = f"us{symbol.upper()}"
            else:
                continue
            tencent_to_pair[tencent_symbol] = (symbol, market)
            tencent_symbols.append(tencent_symbol)
            
        if not tencent_symbols:
            return results

        query_str = ",".join(f"s_{ts}" for ts in tencent_symbols)
        url = f"http://qt.gtimg.cn/q={query_str}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            response = self.client.get(url, headers=headers)
            response.raise_for_status()
            content = response.content.decode("gbk")
            
            for line in content.splitlines():
                line = line.strip()
                if not line or "=" not in line:
                    continue
                left, right = line.split("=", 1)
                ts_match = re.search(r'v_s_(hk|sh|sz|us)\w+', left)
                if not ts_match:
                    continue
                ts = ts_match.group(0).replace("v_s_", "").strip()
                
                pair = tencent_to_pair.get(ts)
                if not pair:
                    continue
                
                parts = right.strip('";').split("~")
                if len(parts) >= 6:
                    price = safe_float(parts[3])
                    change = safe_float(parts[4])
                    change_percent = safe_float(parts[5])
                    market = pair[1]
                    currency = "CNY" if market == "CN" else "HKD" if market == "HK" else "USD"
                    market_state = get_chinese_market_state(market) if market in ("CN", "HK") else None
                    
                    results[pair] = QuoteData(
                        symbol=pair[0],
                        market=market,
                        price=price,
                        previous_close=price - change if price is not None and change is not None else None,
                        change=change,
                        change_percent=change_percent,
                        currency=currency,
                        exchange="SSE/SZSE" if market == "CN" else "HKEX" if market == "HK" else "US",
                        source=self.source_name,
                        updated_at=datetime.now(timezone.utc),
                        market_state=market_state,
                    )
        except Exception as e:
            print(f"Tencent batch quote fetch failed: {e}")
            
        return results

