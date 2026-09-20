from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Protocol

from src.models import Fundamentals, PriceHistory, Snapshot
from src.universe import MARKET_TICKER, QUALITY_UNIVERSE

logger = logging.getLogger(__name__)


class MarketDataProvider(Protocol):
    def load(self, tickers: tuple[str, ...] | None = None) -> tuple[list[Snapshot], PriceHistory]:
        """Return company snapshots plus the market (SPY) history."""


def get_provider() -> MarketDataProvider:
    flag = os.environ.get("USE_MOCK_DATA", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        from src.fixtures import FixtureProvider

        return FixtureProvider()
    return YahooProvider()


class YahooProvider(MarketDataProvider):
    def load(self, tickers: tuple[str, ...] | None = None) -> tuple[list[Snapshot], PriceHistory]:
        import yfinance as yf

        symbols = list(tickers or QUALITY_UNIVERSE)
        download_list = symbols + [MARKET_TICKER]
        history = yf.download(
            download_list,
            period="1y",
            interval="1d",
            auto_adjust=True,
            threads=True,
            progress=False,
            group_by="ticker",
        )
        if history is None or history.empty:
            raise RuntimeError("Yahoo Finance returned no price history.")

        spy_prices = _extract_prices(history, MARKET_TICKER)
        snapshots: list[Snapshot] = []

        prelim: list[tuple[str, PriceHistory, float, float]] = []
        for ticker in symbols:
            try:
                prices = _extract_prices(history, ticker)
                current = prices.close[-1]
                high_52w = max(prices.high)
                if current <= 0:
                    continue
                prelim.append((ticker, prices, current, high_52w))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping %s prices: %s", ticker, exc)

        fundamentals_map = _fetch_fundamentals([ticker for ticker, *_ in prelim])

        for ticker, prices, current, high_52w in prelim:
            info = fundamentals_map.get(ticker, {})
            fundamentals = Fundamentals(
                name=str(info.get("shortName") or info.get("longName") or ticker),
                sector=str(info.get("sector") or "Unknown"),
                roe=_maybe_float(info.get("returnOnEquity")),
                operating_margin=_maybe_float(info.get("operatingMargins")),
                profit_margin=_maybe_float(info.get("profitMargins")),
                debt_to_equity=_maybe_float(info.get("debtToEquity")),
                current_ratio=_maybe_float(info.get("currentRatio")),
                free_cash_flow=_maybe_float(info.get("freeCashflow")),
                earnings_growth=_maybe_float(info.get("earningsGrowth")),
                trailing_pe=_maybe_float(info.get("trailingPE")),
                return_on_assets=_maybe_float(info.get("returnOnAssets")),
            )
            live_price = _maybe_float(info.get("currentPrice")) or _maybe_float(info.get("regularMarketPrice"))
            live_high = _maybe_float(info.get("fiftyTwoWeekHigh"))
            snapshots.append(
                Snapshot(
                    ticker=ticker,
                    fundamentals=fundamentals,
                    prices=prices,
                    current_price=live_price or current,
                    high_52w=max(live_high or 0.0, high_52w),
                )
            )
        return snapshots, spy_prices


def _extract_prices(history, ticker: str) -> PriceHistory:
    if getattr(history.columns, "nlevels", 1) > 1:
        frame = history[ticker]
    else:
        frame = history
    close = [float(v) for v in frame["Close"].dropna().tolist()]
    high_col = "High" if "High" in frame.columns else "Close"
    high = [float(v) for v in frame[high_col].dropna().tolist()]
    if len(close) < 30:
        raise ValueError(f"{ticker} has insufficient history")
    return PriceHistory(close=close, high=high)


def _maybe_float(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _fetch_fundamentals(tickers: list[str]) -> dict[str, dict]:
    import yfinance as yf

    results: dict[str, dict] = {}
    if not tickers:
        return results

    def _one(ticker: str) -> tuple[str, dict]:
        try:
            info = yf.Ticker(ticker).info or {}
            return ticker, info if isinstance(info, dict) else {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fundamentals failed for %s: %s", ticker, exc)
            return ticker, {}

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_one, ticker) for ticker in tickers]
        for future in as_completed(futures):
            ticker, info = future.result()
            results[ticker] = info
    return results
