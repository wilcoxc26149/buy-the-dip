from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode

from src.httputil import get_json
from src.models import Fundamentals
from src.universe import SECTORS


def load_vendor_fundamentals(tickers: list[str]) -> dict[str, Fundamentals]:
    results: dict[str, Fundamentals] = {}
    missing = list(tickers)
    if os.environ.get("FINNHUB_API_KEY") and missing:
        filled = _load_finnhub(missing)
        results.update(filled)
        missing = [ticker for ticker in missing if ticker not in results]
    if os.environ.get("ALPHA_VANTAGE_API_KEY") and missing:
        results.update(_load_alpha_vantage(missing))
    return results


def _load_finnhub(tickers: list[str]) -> dict[str, Fundamentals]:
    token = os.environ["FINNHUB_API_KEY"]
    results: dict[str, Fundamentals] = {}

    def _one(ticker: str) -> tuple[str, Fundamentals | None]:
        query = urlencode({"symbol": ticker, "metric": "all", "token": token})
        payload = get_json(f"https://finnhub.io/api/v1/stock/metric?{query}", timeout=20)
        metric = payload.get("metric") or {}
        if not metric:
            return ticker, None
        return ticker, _from_vendor_metrics(
            ticker,
            source="Finnhub metrics",
            name=ticker,
            roe=_pct_or_decimal(metric.get("roeTTM") or metric.get("roeRfy")),
            operating_margin=_pct_or_decimal(metric.get("operatingMarginTTM")),
            profit_margin=_pct_or_decimal(metric.get("netProfitMarginTTM")),
            debt_to_equity=_maybe_float(metric.get("totalDebt/totalEquityAnnual") or metric.get("totalDebt/totalEquityQuarterly")),
            current_ratio=_maybe_float(metric.get("currentRatioQuarterly") or metric.get("currentRatioAnnual")),
            free_cash_flow=_maybe_float(metric.get("freeCashFlowAnnual") or metric.get("focfCagr5Y")),
            earnings_growth=_pct_or_decimal(metric.get("epsGrowthTTMYoy") or metric.get("epsGrowth3Y")),
            trailing_pe=_maybe_float(metric.get("peNormalizedAnnual") or metric.get("peTTM")),
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(_one, ticker) for ticker in tickers]
        for future in as_completed(futures):
            try:
                ticker, fundamentals = future.result()
            except Exception:
                continue
            if fundamentals is not None:
                results[ticker] = fundamentals
    return results


def _load_alpha_vantage(tickers: list[str]) -> dict[str, Fundamentals]:
    key = os.environ["ALPHA_VANTAGE_API_KEY"]
    results: dict[str, Fundamentals] = {}
    # Free keys are tiny; only fill a few gaps.
    for ticker in tickers[:8]:
        try:
            query = urlencode({"function": "OVERVIEW", "symbol": ticker, "apikey": key})
            payload = get_json(f"https://www.alphavantage.co/query?{query}", timeout=20)
        except Exception:
            continue
        if not payload or "Symbol" not in payload:
            continue
        results[ticker] = _from_vendor_metrics(
            ticker,
            source="Alpha Vantage OVERVIEW",
            name=str(payload.get("Name") or ticker),
            roe=_pct_or_decimal(payload.get("ReturnOnEquityTTM")),
            operating_margin=_pct_or_decimal(payload.get("OperatingMarginTTM")),
            profit_margin=_pct_or_decimal(payload.get("ProfitMargin")),
            debt_to_equity=_maybe_float(payload.get("DebtToEquity") or payload.get("QuarterlyRevenueGrowthYOY")),
            current_ratio=None,
            free_cash_flow=None,
            earnings_growth=_pct_or_decimal(payload.get("QuarterlyEarningsGrowthYOY")),
            trailing_pe=_maybe_float(payload.get("PERatio")),
        )
    return results


def _from_vendor_metrics(
    ticker: str,
    *,
    source: str,
    name: str,
    roe: float | None,
    operating_margin: float | None,
    profit_margin: float | None,
    debt_to_equity: float | None,
    current_ratio: float | None,
    free_cash_flow: float | None,
    earnings_growth: float | None,
    trailing_pe: float | None,
) -> Fundamentals:
    return Fundamentals(
        name=name,
        sector=SECTORS.get(ticker, "Unknown"),
        roe=roe,
        operating_margin=operating_margin,
        profit_margin=profit_margin,
        debt_to_equity=debt_to_equity,
        current_ratio=current_ratio,
        free_cash_flow=free_cash_flow,
        earnings_growth=earnings_growth,
        trailing_pe=trailing_pe,
        source=source,
        research_note=f"{source} fill-in for {name}.",
    )


def _maybe_float(value) -> float | None:
    if value in (None, "None", "N/A", "-", ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _pct_or_decimal(value) -> float | None:
    number = _maybe_float(value)
    if number is None:
        return None
    # Vendor APIs mix 0.18 and 18 for 18%.
    if abs(number) > 2:
        return number / 100.0
    return number
