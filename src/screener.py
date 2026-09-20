from __future__ import annotations

from src.analysis import to_opportunity
from src.data import MarketDataProvider, get_provider
from src.models import Opportunity, PriceHistory, Snapshot
from src.scoring import (
    below_long_ma,
    buy_in_price,
    confidence_score,
    drawdown_from_high,
    macro_score,
    quality_score,
    sell_out_price,
    spy_correlation,
)
from src.universe import (
    MAX_COMPANIES,
    MAX_HOLD_DAYS,
    MIN_COMPANIES,
    MIN_HOLD_DAYS,
)


class ScreenError(ValueError):
    """User-facing validation error."""


def validate_inputs(max_quote_price: float, hold_days: int, company_count: int) -> tuple[float, int, int]:
    try:
        max_quote_price = float(max_quote_price)
        hold_days = int(hold_days)
        company_count = int(company_count)
    except (TypeError, ValueError) as exc:
        raise ScreenError("Max price, hold days, and company count must be numbers.") from exc

    if max_quote_price <= 0:
        raise ScreenError("Max quote price must be greater than zero.")
    if hold_days < MIN_HOLD_DAYS:
        raise ScreenError(
            f"Hold timeframe must be at least {MIN_HOLD_DAYS} days. This screen is not built for day trading."
        )
    if hold_days > MAX_HOLD_DAYS:
        raise ScreenError(f"Hold timeframe cannot exceed {MAX_HOLD_DAYS} days.")
    if company_count < MIN_COMPANIES or company_count > MAX_COMPANIES:
        raise ScreenError(f"Company count must be between {MIN_COMPANIES} and {MAX_COMPANIES}.")
    return max_quote_price, hold_days, company_count


def screen(
    max_quote_price: float,
    hold_days: int,
    company_count: int,
    provider: MarketDataProvider | None = None,
) -> list[Opportunity]:
    max_quote_price, hold_days, company_count = validate_inputs(
        max_quote_price, hold_days, company_count
    )
    provider = provider or get_provider()
    snapshots, spy = provider.load()
    market_drawdown = drawdown_from_high(spy.close[-1], max(spy.high))

    ranked: list[tuple[float, Opportunity]] = []
    for snapshot in snapshots:
        opportunity = _evaluate(snapshot, spy, market_drawdown, max_quote_price, hold_days)
        if opportunity is None:
            continue
        rank = (
            0.45 * opportunity.confidence
            + 0.30 * opportunity.expected_return_pct
            + 0.25 * opportunity.quality_score
        )
        ranked.append((rank, opportunity))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:company_count]]


def _evaluate(
    snapshot: Snapshot,
    spy: PriceHistory,
    market_drawdown: float,
    max_quote_price: float,
    hold_days: int,
) -> Opportunity | None:
    if snapshot.current_price > max_quote_price:
        return None

    quality, complete = quality_score(snapshot.fundamentals)
    correlation = spy_correlation(snapshot.prices, spy)
    stock_drawdown = drawdown_from_high(snapshot.current_price, snapshot.high_52w)
    macro = macro_score(
        stock_drawdown=stock_drawdown,
        market_drawdown=market_drawdown,
        correlation=correlation,
        below_ma=below_long_ma(snapshot.prices.close),
        earnings_growth=snapshot.fundamentals.earnings_growth,
    )

    if quality < 50 or macro < 35:
        return None

    buy_in = buy_in_price(snapshot.prices.close, snapshot.current_price)
    if buy_in > max_quote_price:
        return None
    sell_out = sell_out_price(
        current=snapshot.current_price,
        high_52w=snapshot.high_52w,
        hold_days=hold_days,
        quality=quality,
    )
    if sell_out < buy_in * 1.03:
        return None

    expected_return_pct = (sell_out - buy_in) / buy_in * 100.0
    confidence = confidence_score(
        quality=quality,
        macro=macro,
        correlation=correlation,
        hold_days=hold_days,
        expected_return_pct=expected_return_pct,
        fundamentals_complete=complete,
    )
    return to_opportunity(
        snapshot,
        buy_in=buy_in,
        sell_out=sell_out,
        hold_days=hold_days,
        quality=quality,
        macro=macro,
        confidence=confidence,
        drawdown_pct=stock_drawdown,
        spy_correlation=correlation,
        market_drawdown=market_drawdown,
    )
