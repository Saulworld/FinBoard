from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

from .config import get_settings
from .providers import FinnhubProvider, NewsItem, QuoteData, TwelveDataProvider, YahooFinanceProvider, TencentFinanceProvider
from .utils import (
    MARKET_LABELS,
    format_datetime,
    format_large_number,
    format_money,
    format_number,
    format_percent,
    normalize_market,
    normalize_symbol,
    safe_float,
    translate_text,
)


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[datetime, Any]] = {}

    def get(self, key: str) -> Any | None:
        payload = self._store.get(key)
        if not payload:
            return None
        expires_at, value = payload
        if expires_at <= datetime.utcnow():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> Any:
        seconds = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        self._store[key] = (datetime.utcnow() + timedelta(seconds=seconds), value)
        return value


@dataclass
class QuoteView:
    symbol: str
    market: str
    market_label: str
    price: float | None
    price_text: str
    previous_close: float | None
    previous_close_text: str
    change: float | None
    change_text: str
    change_percent: float | None
    change_percent_text: str
    source: str
    updated_at_text: str
    currency: str | None
    exchange: str | None
    css_class: str
    market_state: str | None = None


def _label_for_recommendation(mean_value: float | None, key_value: str | None = None) -> str:
    if key_value:
        text = str(key_value).strip().lower()
        mapping = {
            "strong_buy": "强烈看多",
            "buy": "偏多",
            "hold": "中性",
            "underperform": "偏空",
            "sell": "偏空",
        }
        if text in mapping:
            return mapping[text]
    if mean_value is None:
        return "暂无一致观点"
    if mean_value <= 1.6:
        return "强烈看多"
    if mean_value <= 2.4:
        return "偏多"
    if mean_value <= 3.2:
        return "中性"
    if mean_value <= 4.0:
        return "偏空"
    return "强烈看空"


def _merge_news(preferred: list[NewsItem], fallback: list[NewsItem], limit: int = 12) -> list[NewsItem]:
    seen: set[str] = set()
    merged: list[NewsItem] = []
    for item in [*preferred, *fallback]:
        if item.url in seen:
            continue
        seen.add(item.url)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


class MarketDataService:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.yahoo = YahooFinanceProvider()
        self.finnhub = FinnhubProvider(settings.finnhub_api_key, settings.request_timeout_seconds)
        self.twelve_data = TwelveDataProvider(settings.twelve_data_api_key, settings.request_timeout_seconds)
        self.tencent = TencentFinanceProvider()
        self.quote_cache = TTLCache(settings.quote_cache_seconds)
        self.detail_cache = TTLCache(settings.detail_cache_seconds)

    def _quote_cache_key(self, symbol: str, market: str) -> str:
        return f"quote::{market}::{symbol}"

    def _detail_cache_key(self, symbol: str, market: str) -> str:
        return f"detail::{market}::{symbol}"

    def get_exchange_rate(self, source_currency: str, target_currency: str) -> float | None:
        """Return a live FX conversion rate, using Yahoo direct and inverse pairs."""
        source = (source_currency or "").strip().upper()
        target = (target_currency or "").strip().upper()
        if not source or not target:
            return None
        if source == target:
            return 1.0

        cache_key = f"fx::{source}::{target}"
        cached = self.quote_cache.get(cache_key)
        if cached is not None:
            return cached

        rate = None
        try:
            direct = self.yahoo.get_quote(f"{source}{target}=X", "US")
            if direct.price is not None and direct.price > 0:
                rate = direct.price
        except Exception:
            pass

        if rate is None:
            try:
                inverse = self.yahoo.get_quote(f"{target}{source}=X", "US")
                if inverse.price is not None and inverse.price > 0:
                    rate = 1 / inverse.price
            except Exception:
                pass

        return self.quote_cache.set(cache_key, rate, ttl_seconds=None if rate is not None else 30)

    def _format_quote(self, quote: QuoteData) -> QuoteView:
        css_class = "flat"
        if (quote.change or 0) > 0:
            css_class = "up"
        elif (quote.change or 0) < 0:
            css_class = "down"
        
        price_text = format_money(quote.price, quote.currency)
        if quote.market_state == "PRE":
            price_text = f"{price_text} (盘前)"
        elif quote.market_state == "POST":
            price_text = f"{price_text} (盘后)"

        return QuoteView(
            symbol=quote.symbol,
            market=quote.market,
            market_label=MARKET_LABELS.get(quote.market, quote.market),
            price=quote.price,
            price_text=price_text,
            previous_close=quote.previous_close,
            previous_close_text=format_money(quote.previous_close, quote.currency),
            change=quote.change,
            change_text=format_money(quote.change, quote.currency),
            change_percent=quote.change_percent,
            change_percent_text=format_percent(quote.change_percent),
            source=quote.source or "未知来源",
            updated_at_text=format_datetime(quote.updated_at),
            currency=quote.currency,
            exchange=quote.exchange,
            css_class=css_class,
            market_state=quote.market_state,
        )

    def get_quote(self, symbol_input: str, market_input: str, preferred_provider: str | dict | None = None, bypass_cache: bool = False) -> QuoteView:
        market = normalize_market(market_input)
        symbol = normalize_symbol(symbol_input, market)

        pref = preferred_provider
        if isinstance(preferred_provider, dict):
            pref = preferred_provider.get(market, "auto")

        cache_key = self._quote_cache_key(symbol, market)
        if pref and pref != "auto":
            cache_key = f"{cache_key}::provider::{pref}"

        if not bypass_cache:
            cached = self.quote_cache.get(cache_key)
            if cached:
                return cached

        providers = []
        if pref == "yahoo":
            providers = [self.yahoo]
        elif pref == "tencent" and market in {"CN", "HK"}:
            providers = [self.tencent, self.yahoo]
        elif pref == "twelve_data" and market in {"US", "ETF"} and self.twelve_data.available():
            providers = [self.twelve_data, self.yahoo]
        elif pref == "finnhub" and market in {"US", "ETF"} and self.finnhub.available():
            providers = [self.finnhub, self.yahoo]
        else:
            if market in {"CN", "HK"}:
                providers.append(self.tencent)
            elif market in {"US", "ETF"}:
                if self.twelve_data.available():
                    providers.append(self.twelve_data)
                if self.finnhub.available():
                    providers.append(self.finnhub)
            providers.append(self.yahoo)
            if market in {"US", "ETF"}:
                providers.append(self.tencent)

        raw_quote = QuoteData(symbol=symbol, market=market)
        success = False
        for provider in providers:
            try:
                raw_quote = provider.get_quote(symbol, market)
                if raw_quote.price is not None:
                    success = True
                    break
            except Exception:
                continue

        view = self._format_quote(raw_quote)
        ttl = None if success else 60
        return self.quote_cache.set(cache_key, view, ttl_seconds=ttl)

    def get_quotes_batch(self, symbols_with_markets: list[tuple[str, str]], preferred_provider: str | dict | None = None, bypass_cache: bool = False) -> dict[tuple[str, str], QuoteView]:
        if not symbols_with_markets:
            return {}
        unique_pairs = list(dict.fromkeys(symbols_with_markets))
        results = {}

        if not bypass_cache:
            missing_pairs = []
            for pair in unique_pairs:
                sym, mkt = pair
                market = normalize_market(mkt)
                pref = preferred_provider
                if isinstance(preferred_provider, dict):
                    pref = preferred_provider.get(market, "auto")

                cache_key = self._quote_cache_key(sym, market)
                if pref and pref != "auto":
                    cache_key = f"{cache_key}::provider::{pref}"
                cached = self.quote_cache.get(cache_key)
                if cached:
                    results[pair] = cached
                else:
                    missing_pairs.append(pair)
            unique_pairs = missing_pairs
            if not unique_pairs:
                return {pair: results.get(pair) for pair in symbols_with_markets if pair in results}
        
        cn_hk_pairs = []
        other_pairs = []
        for pair in unique_pairs:
            sym, mkt = pair
            market = normalize_market(mkt)
            pref = preferred_provider
            if isinstance(preferred_provider, dict):
                pref = preferred_provider.get(market, "auto")

            if market in {"CN", "HK"} and (pref in {"tencent", "auto", None}):
                cn_hk_pairs.append(pair)
            else:
                other_pairs.append(pair)
        if cn_hk_pairs:
            try:
                tencent_results = self.tencent.get_quotes_batch(cn_hk_pairs)
                for pair, raw_quote in tencent_results.items():
                    if raw_quote.price is not None:
                        sym, mkt = pair
                        market = normalize_market(mkt)
                        pref = preferred_provider
                        if isinstance(preferred_provider, dict):
                            pref = preferred_provider.get(market, "auto")

                        cache_key = self._quote_cache_key(pair[0], pair[1])
                        if pref and pref != "auto":
                            cache_key = f"{cache_key}::provider::{pref}"
                        view = self._format_quote(raw_quote)
                        results[pair] = self.quote_cache.set(cache_key, view)
            except Exception as e:
                print(f"Batch fetch for CN/HK symbols via Tencent failed: {e}")
                
            for pair in cn_hk_pairs:
                if pair not in results:
                    other_pairs.append(pair)

        pref_us = preferred_provider
        if isinstance(preferred_provider, dict):
            pref_us = preferred_provider.get("US", "auto")

        use_yahoo_batch = (
            pref_us == "yahoo"
            or (pref_us in {None, "auto"} and not self.twelve_data.available() and not self.finnhub.available())
        )
        if use_yahoo_batch:
            yahoo_batch_pairs = [
                pair for pair in other_pairs
                if normalize_market(pair[1]) in {"US", "ETF"}
            ]
            if yahoo_batch_pairs:
                try:
                    yahoo_results = self.yahoo.get_quotes_batch(yahoo_batch_pairs)
                    for pair, raw_quote in yahoo_results.items():
                        if raw_quote.price is not None:
                            sym, mkt = pair
                            market = normalize_market(mkt)
                            pref = preferred_provider
                            if isinstance(preferred_provider, dict):
                                pref = preferred_provider.get(market, "auto")

                            cache_key = self._quote_cache_key(pair[0], pair[1])
                            if pref and pref != "auto":
                                cache_key = f"{cache_key}::provider::{pref}"
                            view = self._format_quote(raw_quote)
                            results[pair] = self.quote_cache.set(cache_key, view)
                except Exception as e:
                    print(f"Batch fetch for US/ETF symbols via Yahoo failed: {e}")
                other_pairs = [pair for pair in other_pairs if pair not in results]

        if other_pairs:
            from concurrent.futures import ThreadPoolExecutor
            def _fetch(pair):
                sym, mkt = pair
                market = normalize_market(mkt)
                pref = preferred_provider
                if isinstance(preferred_provider, dict):
                    pref = preferred_provider.get(market, "auto")
                try:
                    return pair, self.get_quote(sym, mkt, pref, bypass_cache=bypass_cache)
                except Exception:
                    symbol = normalize_symbol(sym, market)
                    return pair, self._format_quote(QuoteData(symbol=symbol, market=market))
            with ThreadPoolExecutor(max_workers=min(len(other_pairs), 15)) as executor:
                other_results = dict(executor.map(_fetch, other_pairs))
            results.update(other_results)
            
        return {pair: results.get(pair) for pair in symbols_with_markets if pair in results}

    def get_empty_quote(self, symbol_input: str, market_input: str) -> QuoteView:
        market = normalize_market(market_input)
        symbol = normalize_symbol(symbol_input, market)
        return QuoteView(
            symbol=symbol,
            market=market,
            market_label=MARKET_LABELS.get(market, market),
            price=None,
            price_text="--",
            previous_close=None,
            previous_close_text="--",
            change=None,
            change_text="--",
            change_percent=None,
            change_percent_text="--",
            source="等待刷新...",
            updated_at_text="--",
            currency=None,
            exchange=None,
            css_class="flat",
            market_state=None,
        )

    def lookup_name(self, symbol_input: str, market_input: str) -> str:
        market = normalize_market(market_input)
        symbol = normalize_symbol(symbol_input, market)
        info = self.yahoo.get_profile(symbol)
        return info.get("shortName") or info.get("longName") or symbol

    def get_stock_detail(self, symbol_input: str, market_input: str, preferred_provider: str | dict | None = None, bypass_cache: bool = False) -> dict[str, Any]:
        market = normalize_market(market_input)
        symbol = normalize_symbol(symbol_input, market)

        pref = preferred_provider
        if isinstance(preferred_provider, dict):
            pref = preferred_provider.get(market, "auto")

        cache_key = self._detail_cache_key(symbol, market)
        if pref and pref != "auto":
            cache_key = f"{cache_key}::provider::{pref}"

        if not bypass_cache:
            cached = self.detail_cache.get(cache_key)
            if cached:
                return cached

        from concurrent.futures import ThreadPoolExecutor, wait

        tasks = {
            "quote": lambda: self.get_quote(symbol, market, pref),
            "yahoo_profile": lambda: self.yahoo.get_profile(symbol),
            "yahoo_fundamentals": lambda: self.yahoo.get_fundamentals(symbol, {}),
            "yahoo_consensus": lambda: self.yahoo.get_analyst_view(symbol, {}),
            "history": lambda: self.yahoo.get_history(symbol),
            "yahoo_news": lambda: self.yahoo.get_news(symbol),
        }

        if market in {"US", "ETF"} and self.finnhub.available():
            tasks["finnhub_profile"] = lambda: self.finnhub.get_profile(symbol)
            tasks["finnhub_metrics"] = lambda: self.finnhub.get_basic_financials(symbol)
            tasks["finnhub_news"] = lambda: self.finnhub.get_news(symbol)
            tasks["finnhub_consensus"] = lambda: self.finnhub.get_consensus(symbol)

        results = {}
        executor = ThreadPoolExecutor(max_workers=len(tasks))
        future_to_key = {executor.submit(func): key for key, func in tasks.items()}
        done, pending = wait(future_to_key, timeout=self.settings.detail_request_budget_seconds)
        for future in done:
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as e:
                print(f"Error fetching {key}: {e}")
        for future in pending:
            key = future_to_key[future]
            print(f"Timed out fetching {key}; returning partial detail for {symbol}.")
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)

        for key in tasks:
            if key in results:
                continue
            if key == "quote":
                results[key] = self.get_empty_quote(symbol, market)
            elif key in ("yahoo_profile", "yahoo_fundamentals", "yahoo_consensus", "finnhub_profile", "finnhub_metrics", "finnhub_consensus"):
                results[key] = {}
            elif key in ("history", "yahoo_news", "finnhub_news"):
                results[key] = []
        is_partial = bool(pending)

        quote = results.get("quote") or self.get_empty_quote(symbol, market)
        yahoo_profile = results.get("yahoo_profile") or {}
        yahoo_fundamentals = results.get("yahoo_fundamentals") or {}
        yahoo_consensus = results.get("yahoo_consensus") or {}
        history = results.get("history") or []
        yahoo_news = results.get("yahoo_news") or []

        finnhub_profile = results.get("finnhub_profile") or {}
        finnhub_metrics = results.get("finnhub_metrics") or {}
        finnhub_news = results.get("finnhub_news") or []
        finnhub_consensus = results.get("finnhub_consensus") or {}

        info = {**finnhub_profile, **yahoo_profile}
        news = _merge_news(finnhub_news, yahoo_news)

        # 开启多线程并行翻译新闻标题和摘要，避免阻塞页面加载
        if news and self.settings.translate_news:
            from concurrent.futures import ThreadPoolExecutor
            def _translate_item(item: NewsItem) -> NewsItem:
                try:
                    translated_title = translate_text(item.title)
                    translated_summary = translate_text(item.summary) if item.summary else ""
                    return NewsItem(
                        title=translated_title,
                        source=item.source,
                        published_at=item.published_at,
                        url=item.url,
                        summary=translated_summary
                    )
                except Exception:
                    return item

            try:
                with ThreadPoolExecutor(max_workers=min(len(news), 10)) as executor:
                    news = list(executor.map(_translate_item, news))
            except Exception:
                pass

        # Merge profile details (info) into yahoo_fundamentals and yahoo_consensus
        yahoo_fundamentals["info"] = info
        
        if not yahoo_consensus.get("recommendation_key"):
            yahoo_consensus["recommendation_key"] = info.get("recommendationKey")
        if not yahoo_consensus.get("analyst_count"):
            yahoo_consensus["analyst_count"] = info.get("numberOfAnalystOpinions")
            
        targets = yahoo_consensus.get("price_targets") or {}
        if not targets.get("mean"):
            targets["mean"] = info.get("targetMeanPrice")
        if not targets.get("high"):
            targets["high"] = info.get("targetHighPrice")
        if not targets.get("low"):
            targets["low"] = info.get("targetLowPrice")
        if not targets.get("numberOfAnalystOpinions"):
            targets["numberOfAnalystOpinions"] = info.get("numberOfAnalystOpinions")
        if not targets.get("recommendationKey"):
            targets["recommendationKey"] = info.get("recommendationKey")
        yahoo_consensus["price_targets"] = targets

        consensus = self._build_consensus(yahoo_consensus, finnhub_consensus, quote.price)
        fundamentals = self._build_fundamental_sections(yahoo_fundamentals, finnhub_metrics, quote.currency)
        highlights = self._build_highlights(yahoo_fundamentals, finnhub_metrics, consensus)

        detail = {
            "symbol": symbol,
            "input_symbol": symbol_input.strip().upper(),
            "market": market,
            "market_label": MARKET_LABELS.get(market, market),
            "name": info.get("shortName") or info.get("longName") or symbol,
            "quote": quote,
            "exchange": info.get("exchange") or quote.exchange or "--",
            "currency": info.get("currency") or quote.currency or "--",
            "website": info.get("website") or "",
            "sector": info.get("sector") or "--",
            "industry": info.get("industry") or "--",
            "business_summary": info.get("longBusinessSummary") or "暂无公司简介。",
            "history_points": history,
            "fundamental_sections": fundamentals,
            "consensus": consensus,
            "news": news,
            "highlights": highlights,
            "partial": is_partial,
        }
        ttl = 15 if is_partial else None
        return self.detail_cache.set(cache_key, detail, ttl_seconds=ttl)

    def _build_consensus(self, yahoo_consensus: dict[str, Any], finnhub_consensus: dict[str, Any], current_price: float | None = None) -> dict[str, Any]:
        targets = yahoo_consensus.get("price_targets") or {}
        mean_target = safe_float(targets.get("mean") or targets.get("targetMeanPrice"))
        high_target = safe_float(targets.get("high") or targets.get("targetHighPrice"))
        low_target = safe_float(targets.get("low") or targets.get("targetLowPrice"))
        analyst_count = yahoo_consensus.get("analyst_count") or finnhub_consensus.get("analyst_count")

        recommendation_mean = safe_float(finnhub_consensus.get("recommendation_mean"))
        recommendation_label = _label_for_recommendation(recommendation_mean, yahoo_consensus.get("recommendation_key"))
        breakdown = finnhub_consensus.get("recommendation_breakdown") or yahoo_consensus.get("recommendation_breakdown") or {}

        # 整理推荐评级明细，统一进行中文规范化
        normalized_breakdown = {}
        for k, v in breakdown.items():
            k_lower = k.lower().replace(" ", "").replace("_", "")
            if "strongbuy" in k_lower:
                normalized_breakdown["强烈买入"] = int(v or 0)
            elif "buy" in k_lower:
                normalized_breakdown["买入"] = int(v or 0)
            elif "hold" in k_lower:
                normalized_breakdown["持有"] = int(v or 0)
            elif "strongsell" in k_lower:
                normalized_breakdown["强烈卖出"] = int(v or 0)
            elif "sell" in k_lower or "underperform" in k_lower:
                normalized_breakdown["卖出"] = int(v or 0)
            else:
                normalized_breakdown[k] = int(v or 0)

        # 补全缺少的常用评级键，以便前端以固定顺序漂亮展示
        display_order = ["强烈买入", "买入", "持有", "卖出", "强烈卖出"]
        final_breakdown = {}
        for key in display_order:
            final_breakdown[key] = normalized_breakdown.get(key, 0)
        # 把其他未匹配的也加进去（如果有的话）
        for key, val in normalized_breakdown.items():
            if key not in final_breakdown:
                final_breakdown[key] = val

        # 重新根据评级分布统计总分析师人数，修正可能的不同步问题
        buys = final_breakdown.get("强烈买入", 0) + final_breakdown.get("买入", 0)
        holds = final_breakdown.get("持有", 0)
        sells = final_breakdown.get("卖出", 0) + final_breakdown.get("强烈卖出", 0)
        total_opinions = buys + holds + sells
        actual_count = analyst_count if analyst_count else (total_opinions if total_opinions > 0 else None)

        points = []
        points.append(f"主流观点判断为：{recommendation_label}")
        if actual_count:
            points.append(f"覆盖分析师评级数量：共 {int(actual_count)} 位")

        if total_opinions > 0:
            buy_pct = (buys / total_opinions) * 100
            hold_pct = (holds / total_opinions) * 100
            sell_pct = (sells / total_opinions) * 100
            points.append(f"态度分布占比：看多 (买入) 占 {buy_pct:.1f}%，中性 (持有) 占 {hold_pct:.1f}%，看空 (卖出) 占 {sell_pct:.1f}%")

        if mean_target is not None:
            points.append(f"一致目标均价为：{mean_target:,.2f}")
            if current_price is not None:
                upside = (mean_target - current_price) / current_price * 100
                if upside > 0:
                    points.append(f"上涨空间估算：当前价格较预期均价有 +{upside:.2f}% 的上涨空间")
                else:
                    points.append(f"估值溢价提示：当前价格已超出一致均价 {abs(upside):.2f}%，存在回调消化估值风险")

        if high_target is not None and low_target is not None:
            points.append(f"目标价范围区间：{low_target:,.2f} ~ {high_target:,.2f}")
            if current_price is not None and (high_target > low_target):
                percentile = (current_price - low_target) / (high_target - low_target) * 100
                if percentile > 80:
                    points.append("估值区间定位：价格已接近分析师预测上限（前 20% 位置），估值相对饱满")
                elif percentile < 20:
                    points.append("估值区间定位：价格处于分析师预测下限附近（后 20% 位置），或已具备一定安全边际")
                else:
                    points.append(f"估值区间定位：当前价格处于预测区间中游（百分位约为 {percentile:.1f}%）")

        # 给出多维度投资建议
        if "强烈看多" in recommendation_label or "偏多" in recommendation_label:
            points.append("策略建议参考：分析师共识强劲。可重点关注绩优回调时的分批低吸机会，注意财报期的基本面兑现。")
        elif "中性" in recommendation_label:
            points.append("策略建议参考：多空观点交织，缺乏强方向引导。建议耐心等待业绩指引或行业重要催化剂出现。")
        elif "偏空" in recommendation_label or "强烈看空" in recommendation_label:
            points.append("策略建议参考：负向共识明显或估值遭集中下调。建议注意资金防御，逢反弹控制仓位，防范破位下行。")

        return {
            "recommendation_label": recommendation_label,
            "recommendation_mean": recommendation_mean,
            "breakdown": breakdown,
            "analyst_count": analyst_count,
            "target_mean": format_number(mean_target),
            "target_high": format_number(high_target),
            "target_low": format_number(low_target),
            "source": finnhub_consensus.get("source") or yahoo_consensus.get("source") or "Yahoo Finance",
            "points": points,
        }

    def _build_highlights(
        self,
        yahoo_fundamentals: dict[str, Any],
        finnhub_metrics: dict[str, Any],
        consensus: dict[str, Any],
    ) -> list[dict[str, str]]:
        info = yahoo_fundamentals.get("info", {})
        revenue_growth = safe_float(finnhub_metrics.get("revenueGrowthTTMYoy") or info.get("revenueGrowth"))
        gross_margin = safe_float(finnhub_metrics.get("grossMarginAnnual") or info.get("grossMargins"))
        roe = safe_float(finnhub_metrics.get("roeTTM") or info.get("returnOnEquity"))
        debt_to_equity = safe_float(finnhub_metrics.get("totalDebt/totalEquityAnnual") or info.get("debtToEquity"))

        highlights = [
            {"label": "收入增速", "value": format_percent(revenue_growth * 100 if revenue_growth and revenue_growth < 1 else revenue_growth)},
            {"label": "毛利率", "value": format_percent(gross_margin * 100 if gross_margin and gross_margin < 1 else gross_margin)},
            {"label": "ROE", "value": format_percent(roe * 100 if roe and roe < 1 else roe)},
            {"label": "资产负债压力", "value": format_number(debt_to_equity)},
            {"label": "主流观点", "value": consensus["recommendation_label"]},
        ]
        return highlights

    def _build_fundamental_sections(
        self,
        yahoo_fundamentals: dict[str, Any],
        finnhub_metrics: dict[str, Any],
        currency: str | None,
    ) -> list[dict[str, Any]]:
        info = yahoo_fundamentals.get("info", {})

        def as_percent(raw_value: float | None) -> str:
            if raw_value is None:
                return "--"
            return format_percent(raw_value * 100 if abs(raw_value) <= 1 else raw_value)

        valuation = {
            "title": "估值与盈利",
            "metrics": [
                {"label": "市值", "value": format_large_number(safe_float(info.get("marketCap")), currency)},
                {"label": "市盈率(TTM)", "value": format_number(safe_float(info.get("trailingPE")))},
                {"label": "预期市盈率", "value": format_number(safe_float(info.get("forwardPE")))},
                {"label": "每股收益 EPS", "value": format_number(safe_float(info.get("trailingEps")))},
                {"label": "股息率", "value": as_percent(safe_float(info.get("dividendYield")))},
            ],
        }

        growth = {
            "title": "成长与质量",
            "metrics": [
                {
                    "label": "营收增速",
                    "value": as_percent(safe_float(finnhub_metrics.get("revenueGrowthTTMYoy") or info.get("revenueGrowth"))),
                },
                {
                    "label": "利润增速",
                    "value": as_percent(safe_float(finnhub_metrics.get("netIncomeGrowthTTMYoy") or info.get("earningsGrowth"))),
                },
                {
                    "label": "营业利润率",
                    "value": as_percent(safe_float(finnhub_metrics.get("operatingMarginAnnual") or info.get("operatingMargins"))),
                },
                {
                    "label": "净利率",
                    "value": as_percent(safe_float(finnhub_metrics.get("netMarginAnnual") or info.get("profitMargins"))),
                },
                {
                    "label": "ROE",
                    "value": as_percent(safe_float(finnhub_metrics.get("roeTTM") or info.get("returnOnEquity"))),
                },
            ],
        }

        balance = {
            "title": "财务结构",
            "metrics": [
                {
                    "label": "流动比率",
                    "value": format_number(safe_float(finnhub_metrics.get("currentRatioAnnual") or info.get("currentRatio"))),
                },
                {
                    "label": "速动比率",
                    "value": format_number(safe_float(finnhub_metrics.get("quickRatioAnnual") or info.get("quickRatio"))),
                },
                {
                    "label": "资产负债率/债务权益",
                    "value": format_number(safe_float(finnhub_metrics.get("totalDebt/totalEquityAnnual") or info.get("debtToEquity"))),
                },
                {
                    "label": "现金储备",
                    "value": format_large_number(safe_float(yahoo_fundamentals.get("latest_cash")), currency),
                },
                {
                    "label": "总债务",
                    "value": format_large_number(safe_float(yahoo_fundamentals.get("latest_total_debt")), currency),
                },
            ],
        }

        cashflow = {
            "title": "最近季度",
            "metrics": [
                {
                    "label": "季度营收",
                    "value": format_large_number(safe_float(yahoo_fundamentals.get("latest_quarter_revenue")), currency),
                },
                {
                    "label": "季度净利润",
                    "value": format_large_number(safe_float(yahoo_fundamentals.get("latest_quarter_net_income")), currency),
                },
                {
                    "label": "经营现金流",
                    "value": format_large_number(safe_float(yahoo_fundamentals.get("latest_quarter_operating_cashflow")), currency),
                },
                {
                    "label": "自由现金流",
                    "value": format_large_number(safe_float(info.get("freeCashflow")), currency),
                },
                {
                    "label": "账面价值/股",
                    "value": format_number(safe_float(info.get("bookValue"))),
                },
            ],
        }

        return [valuation, growth, balance, cashflow]


@lru_cache(maxsize=1)
def get_market_data_service() -> MarketDataService:
    return MarketDataService()
