from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Protocol

from src.models import Fundamentals, PriceHistory, Snapshot
from src.universe import MARKET_TICKER, QUALITY_UNIVERSE

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, tuple[list[Snapshot], PriceHistory]]] = {}
_CACHE_TTL_SECONDS = 15 * 60


class MarketDataProvider(Protocol):
    def load(self, tickers: tuple[str, ...] | None = None) -> tuple[list[Snapshot], PriceHistory]:
        """Return company snapshots plus the market (SPY) history."""


def get_provider() -> MarketDataProvider:
    flag = os.environ.get("USE_MOCK_DATA", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        from src.fixtures import FixtureProvider

        return FixtureProvider()
    backend = os.environ.get("MARKET_DATA_PROVIDER", "research").strip().lower()
    if backend in {"yahoo", "yfinance"}:
        return YahooProvider()
    return ResearchProvider()


class ResearchProvider:
    """Prices from Yahoo's chart API; company research from SEC EDGAR companyfacts."""

    def load(self, tickers: tuple[str, ...] | None = None) -> tuple[list[Snapshot], PriceHistory]:
        from src.prices import load_yahoo_charts
        from src.research import load_research_fundamentals

        symbols = list(tickers or QUALITY_UNIVERSE)
        cache_key = "research:" + ",".join(symbols)
        cached = _CACHE.get(cache_key)
        if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

        charts = load_yahoo_charts(symbols + [MARKET_TICKER])
        if MARKET_TICKER not in charts:
            return YahooProvider().load(tickers)

        spy_history, _, _ = charts[MARKET_TICKER]
        priced = [ticker for ticker in symbols if ticker in charts]
        if not priced:
            return YahooProvider().load(tickers)

        research = load_research_fundamentals(priced)
        snapshots: list[Snapshot] = []
        for ticker in priced:
            history, current, high_52w = charts[ticker]
            fundamentals = research.get(
                ticker,
                Fundamentals(name=ticker, sector="Unknown", source="price-only"),
            )
            snapshots.append(
                Snapshot(
                    ticker=ticker,
                    fundamentals=fundamentals,
                    prices=history,
                    current_price=current,
                    high_52w=high_52w,
                )
            )
        payload = (snapshots, spy_history)
        _CACHE[cache_key] = (time.time(), payload)
        return payload


class YahooProvider(MarketDataProvider):
    def load(self, tickers: tuple[str, ...] | None = None) -> tuple[list[Snapshot], PriceHistory]:
        import yfinance as yf

        symbols = list(tickers or QUALITY_UNIVERSE)
        cache_key = ",".join(symbols)
        cached = _CACHE.get(cache_key)
        if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

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

        if not prelim:
            raise RuntimeError(
                "Yahoo Finance returned prices, but no company series could be parsed. Try again in a minute."
            )

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
        payload = (snapshots, spy_prices)
        _CACHE[cache_key] = (time.time(), payload)
        return payload


def _extract_prices(history, ticker: str) -> PriceHistory:
    frame = _frame_for_ticker(history, ticker)
    close_col = _col(frame, "close")
    if close_col is None:
        raise ValueError(f"{ticker} has no Close column")
    high_col = _col(frame, "high") or close_col
    close = [float(v) for v in frame[close_col].dropna().tolist()]
    high = [float(v) for v in frame[high_col].dropna().tolist()]
    if len(close) < 30:
        raise ValueError(f"{ticker} has insufficient history")
    return PriceHistory(close=close, high=high)


def _frame_for_ticker(history, ticker: str):
    cols = history.columns
    if getattr(cols, "nlevels", 1) > 1:
        level0 = set(map(str, cols.get_level_values(0)))
        level1 = set(map(str, cols.get_level_values(1)))
        if ticker in level0:
            return history[ticker]
        if ticker in level1:
            return history.xs(ticker, axis=1, level=1)
        raise ValueError(f"{ticker} missing from download columns")
    return history


def _col(frame, name: str) -> str | None:
    wanted = name.lower()
    for column in frame.columns:
        if str(column).lower() == wanted:
            return column
    return None


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
        info: dict = {}
        try:
            handle = yf.Ticker(ticker)
            try:
                fast = handle.fast_info
                info.update(
                    {
                        "currentPrice": getattr(fast, "last_price", None),
                        "fiftyTwoWeekHigh": getattr(fast, "year_high", None),
                    }
                )
            except Exception:  # noqa: BLE001
                pass
            try:
                full = handle.info or {}
                if isinstance(full, dict):
                    info.update(full)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Fundamentals failed for %s: %s", ticker, exc)
            return ticker, info
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ticker lookup failed for %s: %s", ticker, exc)
            return ticker, {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_one, ticker) for ticker in tickers]
        for future in as_completed(futures):
            try:
                ticker, info = future.result(timeout=12)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Fundamentals timed out: %s", exc)
                continue
            results[ticker] = info
    return results
