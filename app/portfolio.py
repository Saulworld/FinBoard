from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class PortfolioEntry:
    cost_value: float
    cost_currency: str
    market_value: float | None
    market_currency: str


@dataclass(frozen=True)
class PortfolioTotals:
    base_currency: str
    total_cost: float | None
    total_value: float | None
    total_pnl: float | None
    missing_currencies: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_currencies

    @property
    def total_return_percent(self) -> float | None:
        if not self.complete or self.total_cost in (None, 0) or self.total_pnl is None:
            return None
        return (self.total_pnl / self.total_cost) * 100


def calculate_portfolio_totals(
    entries: Iterable[PortfolioEntry],
    base_currency: str,
    rate_getter: Callable[[str, str], float | None],
) -> PortfolioTotals:
    """Convert every holding to one base currency before calculating totals."""
    base = (base_currency or "CNY").strip().upper()
    total_cost = 0.0
    total_value = 0.0
    missing: set[str] = set()

    for entry in entries:
        cost_currency = (entry.cost_currency or base).upper()
        market_currency = (entry.market_currency or cost_currency).upper()
        cost_rate = 1.0 if cost_currency == base else rate_getter(cost_currency, base)
        market_rate = 1.0 if market_currency == base else rate_getter(market_currency, base)

        if cost_rate is None or cost_rate <= 0:
            missing.add(cost_currency)
        else:
            total_cost += entry.cost_value * cost_rate

        if entry.market_value is None:
            missing.add(f"{market_currency}行情")
        elif market_rate is None or market_rate <= 0:
            missing.add(market_currency)
        else:
            total_value += entry.market_value * market_rate

    missing_tuple = tuple(sorted(missing))
    if missing_tuple:
        return PortfolioTotals(base, None, None, None, missing_tuple)

    return PortfolioTotals(base, total_cost, total_value, total_value - total_cost, ())
