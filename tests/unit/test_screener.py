from __future__ import annotations

import pytest

from src.fixtures import FixtureProvider
from src.screener import ScreenError, screen, validate_inputs


def test_default_screen_returns_requested_count():
    results = screen(250, 90, 5, provider=FixtureProvider())
    assert len(results) == 5
    tickers = {item.ticker for item in results}
    assert "JUNK" not in tickers
    assert "NODIP" not in tickers
    assert "COST" not in tickers
    assert tickers <= {"AAPL", "JPM", "HD", "CAT", "V", "NEE", "XOM", "PG", "KO", "MSFT"}


def test_max_quote_price_filters_expensive_names():
    cheap = screen(90, 90, 8, provider=FixtureProvider())
    assert cheap
    assert all(item.current_price <= 90 for item in cheap)
    assert all(item.buy_in <= 90 for item in cheap)


def test_tight_max_price_still_returns_affordable_names():
    results = screen(70, 90, 5, provider=FixtureProvider())
    assert results
    assert all(item.current_price <= 70 for item in results)
    assert {item.ticker for item in results} <= {"KO", "NEE", "XOM", "PG", "JPM", "AAPL"}


def test_buy_in_and_sell_out_are_actionable():
    results = screen(250, 120, 5, provider=FixtureProvider())
    for item in results:
        assert item.buy_in > 0
        assert item.sell_out >= item.buy_in * 1.03
        assert item.hold_days == 120
        assert 0 <= item.confidence <= 100
        assert item.analysis
        assert item.ticker in item.analysis


def test_longer_hold_raises_sell_target():
    short = {item.ticker: item.sell_out for item in screen(250, 30, 4, provider=FixtureProvider())}
    long = {item.ticker: item.sell_out for item in screen(250, 240, 4, provider=FixtureProvider())}
    overlap = set(short) & set(long)
    assert overlap
    assert any(long[ticker] >= short[ticker] for ticker in overlap)


@pytest.mark.parametrize(
    ("price", "days", "count"),
    [
        (0, 90, 5),
        (100, 5, 5),
        (100, 90, 0),
        (100, 90, 20),
    ],
)
def test_validate_inputs_rejects_bad_values(price, days, count):
    with pytest.raises(ScreenError):
        validate_inputs(price, days, count)


def test_validate_inputs_accepts_supported_range():
    assert validate_inputs("150", "45", "3") == (150.0, 45, 3)
