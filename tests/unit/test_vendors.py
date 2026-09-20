from __future__ import annotations

from src.vendors import _from_vendor_metrics, _pct_or_decimal


def test_vendor_percent_values_normalize_to_decimals():
    assert _pct_or_decimal("18.5") == 0.185
    assert _pct_or_decimal(0.22) == 0.22
    assert _pct_or_decimal("N/A") is None


def test_vendor_metrics_mark_the_source():
    fundamentals = _from_vendor_metrics(
        "AAPL",
        source="Finnhub metrics",
        name="Apple Inc.",
        roe=0.4,
        operating_margin=0.3,
        profit_margin=0.25,
        debt_to_equity=50,
        current_ratio=1.2,
        free_cash_flow=1e9,
        earnings_growth=0.1,
        trailing_pe=30,
    )
    assert fundamentals.source == "Finnhub metrics"
    assert "Finnhub" in (fundamentals.research_note or "")
