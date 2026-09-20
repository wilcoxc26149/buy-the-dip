from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fundamentals:
    name: str
    sector: str
    roe: float | None = None
    operating_margin: float | None = None
    profit_margin: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    free_cash_flow: float | None = None
    earnings_growth: float | None = None
    trailing_pe: float | None = None
    return_on_assets: float | None = None
    source: str = "universe"
    research_note: str | None = None


@dataclass
class PriceHistory:
    close: list[float]
    high: list[float]


@dataclass
class Snapshot:
    ticker: str
    fundamentals: Fundamentals
    prices: PriceHistory
    current_price: float
    high_52w: float


@dataclass
class Opportunity:
    ticker: str
    name: str
    sector: str
    current_price: float
    buy_in: float
    sell_out: float
    hold_days: int
    expected_return_pct: float
    confidence: float
    quality_score: float
    macro_score: float
    analysis: str
    drawdown_pct: float
    spy_correlation: float
    pe_ratio: float | None = None
    roe: float | None = None
    extras: dict = field(default_factory=dict)
