from __future__ import annotations

from src.eval import RESEARCH_SOURCES, grade_screen, letter_for
from src.fixtures import FixtureProvider
from src.screener import ScreenResult, screen_detailed
from src.universe import QUALITY_UNIVERSE
from src.ciks import TICKER_CIKS


def test_local_cik_map_covers_the_quality_universe():
    missing = [ticker for ticker in QUALITY_UNIVERSE if ticker not in TICKER_CIKS]
    assert missing == []
    assert all(len(cik) == 10 and cik.isdigit() for cik in TICKER_CIKS.values())


def test_fixture_screen_receives_an_overall_grade():
    result = screen_detailed(250, 90, 5, provider=FixtureProvider())
    assert result.grade is not None
    assert result.grade.letter in {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"}
    assert 60 <= result.grade.score <= 100
    assert "Quality of picks" in result.grade.breakdown
    markdown = result.grade.as_markdown()
    assert "Overall grade" in markdown


def test_empty_screen_grades_as_f():
    empty = ScreenResult(
        opportunities=[],
        scanned=10,
        priced_out=10,
        quality_rejected=0,
        cheapest_over_max=("MSFT", 400.0),
        shallow_backfill=0,
    )
    grade = grade_screen(empty)
    assert grade.letter == "F"
    assert grade.score == 0


def test_letter_boundaries():
    assert letter_for(99) == "A+"
    assert letter_for(84) == "B"
    assert letter_for(50) == "F"


def test_research_sources_are_the_live_backends():
    assert "SEC EDGAR companyfacts" in RESEARCH_SOURCES
    assert "Finnhub metrics" in RESEARCH_SOURCES
    assert "Alpha Vantage OVERVIEW" in RESEARCH_SOURCES
