from __future__ import annotations

from dataclasses import dataclass, field

from src.screener import PREFERRED_DRAWDOWN, ScreenResult


RESEARCH_SOURCES = {"SEC EDGAR companyfacts", "Finnhub metrics", "Alpha Vantage OVERVIEW"}


@dataclass
class ScreenGrade:
    score: int
    letter: str
    breakdown: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_markdown(self) -> str:
        lines = [f"## Overall grade: **{self.letter}** ({self.score}/100)", ""]
        for name, value in self.breakdown.items():
            lines.append(f"- {name}: **{letter_for(value)}** ({value}/100)")
        if self.notes:
            lines.append("")
            lines.extend(f"- {note}" for note in self.notes)
        return "\n".join(lines)


def grade_screen(result: ScreenResult) -> ScreenGrade:
    picks = result.opportunities
    if not picks:
        notes = ["No names were returned, so the screen cannot be graded as a Leeward set."]
        if result.scanned == 0:
            notes.append("No market data was loaded.")
        elif result.priced_out == result.scanned:
            notes.append("Every name was over the max quote price.")
        return ScreenGrade(score=0, letter="F", breakdown={"Returned names": 0}, notes=notes)

    quality = _mean(item.quality_score for item in picks)
    macro = _mean(item.macro_score for item in picks)
    confidence = _mean(item.confidence for item in picks)
    researched = sum(1 for item in picks if item.extras.get("source") in RESEARCH_SOURCES)
    coverage = 100.0 * researched / len(picks)
    true_dips = sum(1 for item in picks if item.drawdown_pct >= PREFERRED_DRAWDOWN * 100)
    dip_share = 100.0 * true_dips / len(picks)
    spreads = [item.sell_out / item.buy_in - 1.0 for item in picks if item.buy_in]
    actionability = 100.0 if spreads and all(spread >= 0.03 for spread in spreads) else 40.0
    if spreads:
        actionability = min(100.0, actionability + 200.0 * (_mean(spreads) - 0.03))
    sectors = {item.sector for item in picks}
    diversification = min(100.0, 40.0 + 20.0 * max(0, len(sectors) - 1))

    breakdown = {
        "Quality of picks": round(quality),
        "Macro dip": round(0.7 * macro + 0.3 * dip_share),
        "Research coverage": round(coverage),
        "Actionable levels": round(min(100.0, actionability)),
        "Confidence": round(confidence),
        "Sector mix": round(diversification),
    }
    score = round(
        0.25 * breakdown["Quality of picks"]
        + 0.25 * breakdown["Macro dip"]
        + 0.15 * breakdown["Research coverage"]
        + 0.15 * breakdown["Actionable levels"]
        + 0.10 * breakdown["Confidence"]
        + 0.10 * breakdown["Sector mix"]
    )
    notes = []
    if coverage < 50:
        notes.append("Most names are missing SEC/vendor 10-K research, so quality is partly a universe prior.")
    if dip_share < 60:
        notes.append("Several names are only a shallow pullback, not a clear macro dip.")
    if result.shallow_backfill:
        notes.append(f"{result.shallow_backfill} slot(s) were backfilled below a 3% drawdown.")
    return ScreenGrade(score=score, letter=letter_for(score), breakdown=breakdown, notes=notes)


def letter_for(score: float) -> str:
    if score >= 97:
        return "A+"
    if score >= 93:
        return "A"
    if score >= 90:
        return "A-"
    if score >= 87:
        return "B+"
    if score >= 83:
        return "B"
    if score >= 80:
        return "B-"
    if score >= 77:
        return "C+"
    if score >= 73:
        return "C"
    if score >= 70:
        return "C-"
    if score >= 60:
        return "D"
    return "F"


def _mean(values) -> float:
    data = list(values)
    if not data:
        return 0.0
    return sum(data) / len(data)
