"""Quality-biased universe of publicly traded companies.

This is not the entire market. Names are chosen because they are typically
large, liquid, and operationally established — the screener still has to
prove each name is well-run and macro-suppressed.
"""

from __future__ import annotations

QUALITY_UNIVERSE: tuple[str, ...] = (
    # Technology
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "AVGO",
    "ORCL",
    "ADBE",
    "CRM",
    "NOW",
    "INTU",
    "CSCO",
    "AMD",
    "QCOM",
    "TXN",
    "IBM",
    # Healthcare
    "UNH",
    "JNJ",
    "LLY",
    "ABBV",
    "MRK",
    "TMO",
    "ABT",
    "DHR",
    "ISRG",
    "SYK",
    "PFE",
    # Financials
    "JPM",
    "V",
    "MA",
    "BRK-B",
    "GS",
    "MS",
    "BLK",
    "SPGI",
    "AXP",
    "BAC",
    # Consumer
    "COST",
    "WMT",
    "HD",
    "PG",
    "KO",
    "PEP",
    "NKE",
    "MCD",
    "SBUX",
    "TJX",
    "LOW",
    # Industrials
    "CAT",
    "HON",
    "UNP",
    "GE",
    "DE",
    "LMT",
    "UPS",
    "ETN",
    "RTX",
    # Energy / materials / other
    "XOM",
    "CVX",
    "LIN",
    "NEE",
    "PLD",
    "NFLX",
    "DIS",
    "TSLA",
)

MARKET_TICKER = "SPY"

MIN_HOLD_DAYS = 14
MAX_HOLD_DAYS = 365
MIN_COMPANIES = 1
MAX_COMPANIES = 12
DEFAULT_MAX_PRICE = 250.0
DEFAULT_HOLD_DAYS = 90
DEFAULT_COMPANIES = 5
