from __future__ import annotations

from src.models import Fundamentals
from src.scoring import buy_in_price, confidence_score, quality_score, sell_out_price


def test_quality_score_prefers_strong_operators():
    strong = Fundamentals(
        name="Strong",
        sector="Technology",
        roe=0.30,
        operating_margin=0.24,
        profit_margin=0.19,
        debt_to_equity=35,
        current_ratio=1.8,
        free_cash_flow=5_000_000_000,
        earnings_growth=0.14,
    )
    weak = Fundamentals(
        name="Weak",
        sector="Unknown",
        roe=0.02,
        operating_margin=0.01,
        profit_margin=-0.04,
        debt_to_equity=280,
        current_ratio=0.7,
        free_cash_flow=-1_000_000,
        earnings_growth=-0.2,
    )
    strong_score, complete = quality_score(strong)
    weak_score, _ = quality_score(weak)
    assert complete is True
    assert strong_score >= 70
    assert weak_score < 50


def test_sell_out_exceeds_current_and_grows_with_time():
    short = sell_out_price(current=100, high_52w=130, hold_days=30, quality=80)
    long = sell_out_price(current=100, high_52w=130, hold_days=200, quality=80)
    assert short >= 103
    assert long >= short


def test_buy_in_uses_current_when_already_near_lows():
    closes = [110, 108, 107, 105, 104, 103, 102, 101, 100, 99] * 3
    assert buy_in_price(closes, 99.0) == 99.0


def test_confidence_stays_in_bounds():
    score = confidence_score(
        quality=80,
        macro=70,
        correlation=0.8,
        hold_days=90,
        expected_return_pct=12,
        fundamentals_complete=True,
    )
    assert 0 <= score <= 100
