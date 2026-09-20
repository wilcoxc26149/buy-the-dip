from __future__ import annotations

import math

import numpy as np

from src.models import Fundamentals, PriceHistory


def _clip(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(min(high, max(low, value)))


def _scale(value: float | None, good: float, great: float, weight: float, reverse: bool = False) -> float:
    if value is None or math.isnan(value):
        return weight * 0.45
    if reverse:
        if value <= great:
            return weight
        if value >= good:
            return 0.0
        return weight * (good - value) / (good - great)
    if value >= great:
        return weight
    if value <= good:
        return 0.0
    return weight * (value - good) / (great - good)


def quality_score(fundamentals: Fundamentals, *, universe_prior: float = 50.0) -> tuple[float, bool]:
    """Score how well-run a company looks. Returns (score, fundamentals_were_complete)."""
    parts = [
        _scale(fundamentals.roe, 0.10, 0.25, 22),
        _scale(fundamentals.operating_margin, 0.08, 0.22, 16),
        _scale(fundamentals.profit_margin, 0.05, 0.18, 12),
        _scale(fundamentals.debt_to_equity, 120, 40, 16, reverse=True),
        _scale(fundamentals.current_ratio, 1.0, 1.6, 8),
        14.0 if fundamentals.free_cash_flow is not None and fundamentals.free_cash_flow > 0 else 4.0,
        _scale(fundamentals.earnings_growth, 0.0, 0.12, 12),
    ]
    known = [
        fundamentals.roe,
        fundamentals.operating_margin,
        fundamentals.profit_margin,
        fundamentals.debt_to_equity,
        fundamentals.current_ratio,
        fundamentals.free_cash_flow,
        fundamentals.earnings_growth,
    ]
    complete = sum(v is not None for v in known) >= 5
    raw = sum(parts)
    # Names in the quality universe get a modest prior so a missing Yahoo
    # info payload does not zero out an otherwise liquid franchise.
    blended = 0.82 * raw + 0.18 * universe_prior
    if not complete:
        blended = max(blended, universe_prior + 5.0)
    return _clip(blended), complete


def _returns(closes: list[float]) -> np.ndarray:
    arr = np.asarray(closes, dtype=float)
    if len(arr) < 2:
        return np.array([])
    prev = np.clip(arr[:-1], 1e-9, None)
    return np.diff(arr) / prev


def spy_correlation(stock: PriceHistory, spy: PriceHistory) -> float:
    stock_rets = _returns(stock.close)
    spy_rets = _returns(spy.close)
    n = min(len(stock_rets), len(spy_rets))
    if n < 20:
        return 0.0
    stock_rets = stock_rets[-n:]
    spy_rets = spy_rets[-n:]
    if np.std(stock_rets) == 0 or np.std(spy_rets) == 0:
        return 0.0
    corr = float(np.corrcoef(stock_rets, spy_rets)[0, 1])
    if math.isnan(corr):
        return 0.0
    return float(max(-1.0, min(1.0, corr)))


def drawdown_from_high(current: float, high_52w: float) -> float:
    if high_52w <= 0:
        return 0.0
    return max(0.0, (high_52w - current) / high_52w)


def below_long_ma(closes: list[float], window: int = 200) -> bool:
    if len(closes) < window:
        window = min(len(closes), 50)
    if window < 20:
        return False
    ma = float(np.mean(closes[-window:]))
    return closes[-1] < ma


def macro_score(
    *,
    stock_drawdown: float,
    market_drawdown: float,
    correlation: float,
    below_ma: bool,
    earnings_growth: float | None,
) -> float:
    """High when a quality name is down with the tape, not because the business broke."""
    # Sweet spot: a real dip, not a collapsed equity.
    if 0.07 <= stock_drawdown <= 0.32:
        dip_pts = 30.0
    elif 0.05 <= stock_drawdown < 0.07:
        dip_pts = 18.0
    elif 0.32 < stock_drawdown <= 0.42:
        dip_pts = 16.0
    else:
        dip_pts = 6.0

    corr_pts = 25.0 * max(0.0, min(1.0, (correlation - 0.25) / 0.60))

    # Macro story: stock is weak *with* the market, not 3x worse.
    if market_drawdown <= 0:
        relative_pts = 8.0 if stock_drawdown >= 0.08 else 4.0
    else:
        ratio = stock_drawdown / max(market_drawdown, 0.01)
        if 0.7 <= ratio <= 2.2:
            relative_pts = 20.0
        elif 0.45 <= ratio < 0.7:
            relative_pts = 12.0
        else:
            relative_pts = 5.0

    ma_pts = 15.0 if below_ma else 5.0
    if earnings_growth is None:
        growth_pts = 5.0
    elif earnings_growth >= 0:
        growth_pts = 10.0
    else:
        growth_pts = 2.0

    return _clip(dip_pts + corr_pts + relative_pts + ma_pts + growth_pts)


def recovery_fraction(hold_days: int, quality: float) -> float:
    base = 1.0 - math.exp(-hold_days / 120.0)
    quality_boost = 0.85 + 0.30 * (quality / 100.0)
    return float(min(1.05, base * min(quality_boost, 1.15)))


def buy_in_price(closes: list[float], current: float) -> float:
    window = closes[-20:] if len(closes) >= 20 else closes
    recent_low = min(window) if window else current
    support = recent_low * 1.01
    if current <= support * 1.03:
        return round(current, 2)
    return round(min(current, max(support, current * 0.98)), 2)


def sell_out_price(
    *,
    current: float,
    high_52w: float,
    hold_days: int,
    quality: float,
) -> float:
    recovered = current + max(0.0, high_52w - current) * recovery_fraction(hold_days, quality)
    vol_cap = current * (1.0 + 0.12 * math.sqrt(hold_days / 90.0) * (1.0 + quality / 200.0))
    ceiling = high_52w * 1.08
    target = min(recovered, vol_cap, ceiling)
    if target <= current:
        target = current * (1.0 + 0.03 * math.sqrt(hold_days / 90.0))
    return round(max(target, current * 1.03), 2)


def confidence_score(
    *,
    quality: float,
    macro: float,
    correlation: float,
    hold_days: int,
    expected_return_pct: float,
    fundamentals_complete: bool,
) -> float:
    recovery_odds = _clip(40 + hold_days / 6.0 + max(0.0, correlation) * 20)
    return_sanity = _clip(expected_return_pct * 4.0, 0, 100)
    raw = (
        0.35 * quality
        + 0.25 * macro
        + 0.20 * recovery_odds
        + 0.20 * return_sanity
    )
    if not fundamentals_complete:
        raw -= 12
    return _clip(raw)
