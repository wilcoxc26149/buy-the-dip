from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.httputil import BROWSER_USER_AGENT, get_json
from src.models import PriceHistory

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"


def load_yahoo_charts(tickers: list[str]) -> dict[str, tuple[PriceHistory, float, float]]:
    """Daily OHLCV via Yahoo's public chart endpoint — no Ticker.info scrape."""
    results: dict[str, tuple[PriceHistory, float, float]] = {}

    def _one(ticker: str) -> tuple[str, tuple[PriceHistory, float, float]]:
        payload = get_json(
            CHART_URL.format(ticker=ticker),
            headers={"User-Agent": BROWSER_USER_AGENT, "Accept": "application/json"},
        )
        return ticker, parse_chart_payload(payload)

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_one, ticker) for ticker in tickers]
        for future in as_completed(futures):
            try:
                ticker, parsed = future.result()
                results[ticker] = parsed
            except Exception:
                continue
    return results


def parse_chart_payload(payload: dict) -> tuple[PriceHistory, float, float]:
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise ValueError("chart result is empty")
    series = result[0]
    quote = ((series.get("indicators") or {}).get("quote") or [{}])[0]
    closes = [float(value) for value in (quote.get("close") or []) if value is not None]
    highs = [float(value) for value in (quote.get("high") or []) if value is not None]
    if len(closes) < 30:
        raise ValueError("insufficient chart history")
    meta = series.get("meta") or {}
    current = float(meta.get("regularMarketPrice") or closes[-1])
    high_52w = float(meta.get("fiftyTwoWeekHigh") or (max(highs) if highs else max(closes)))
    history = PriceHistory(close=closes, high=highs or closes)
    return history, current, max(high_52w, max(history.high))
