from __future__ import annotations

from src.ciks import cik_for
from src.research import load_ticker_ciks


def test_cik_lookup_does_not_use_the_sec_ticker_file():
    mapping = load_ticker_ciks()
    assert mapping["AAPL"] == "0000320193"
    assert mapping["BRK-B"] == "0001067983"
    assert cik_for("aapl") == "0000320193"
    assert cik_for("brk.b") == "0001067983"
    assert cik_for("NOTAREAL") is None
