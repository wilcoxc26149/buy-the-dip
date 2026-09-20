from __future__ import annotations

from src.analysis import build_analysis
from src.models import Fundamentals, PriceHistory, Snapshot


def test_analysis_includes_levels_and_disclaimer():
    snapshot = Snapshot(
        ticker="AAPL",
        fundamentals=Fundamentals(
            name="Apple Inc.",
            sector="Technology",
            roe=0.4,
            free_cash_flow=100,
            earnings_growth=0.1,
            debt_to_equity=40,
            research_note="SEC 10-K research for Apple Inc.; ROE 40%.",
        ),
        prices=PriceHistory(close=[100, 110, 105], high=[102, 112, 108]),
        current_price=105,
        high_52w=130,
    )
    text = build_analysis(
        snapshot,
        buy_in=104,
        sell_out=118,
        hold_days=90,
        quality=82,
        macro=74,
        confidence=77,
        drawdown_pct=0.19,
        spy_correlation=0.81,
        market_drawdown=0.12,
    )
    assert "AAPL" in text
    assert "$104.00" in text
    assert "$118.00" in text
    assert "confidence 77/100" in text
    assert "not a recommendation" in text
    assert "SEC 10-K research" in text
