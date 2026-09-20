from __future__ import annotations

from src.models import Opportunity, Snapshot


def build_analysis(
    snapshot: Snapshot,
    *,
    buy_in: float,
    sell_out: float,
    hold_days: int,
    quality: float,
    macro: float,
    confidence: float,
    drawdown_pct: float,
    spy_correlation: float,
    market_drawdown: float,
) -> str:
    fund = snapshot.fundamentals
    expected = (sell_out - buy_in) / buy_in * 100.0
    roe_text = f"{fund.roe:.0%}" if fund.roe is not None else "n/a"
    fcf_text = "positive free cash flow" if (fund.free_cash_flow or 0) > 0 else "mixed cash-flow history"
    growth_text = (
        f"{fund.earnings_growth:.0%} earnings growth"
        if fund.earnings_growth is not None
        else "limited growth disclosure"
    )
    debt_text = (
        f"debt-to-equity of {fund.debt_to_equity:.0f}"
        if fund.debt_to_equity is not None
        else "an unstated leverage profile"
    )

    if spy_correlation >= 0.6 and drawdown_pct >= market_drawdown * 0.7:
        macro_reason = (
            f"The shares are {drawdown_pct:.0%} below their 52-week high and have moved with "
            f"the broader tape (SPY correlation {spy_correlation:.2f}, market drawdown "
            f"{market_drawdown:.0%}). That pattern looks more like macro pressure than a "
            "company-specific breakdown."
        )
    else:
        macro_reason = (
            f"The stock is {drawdown_pct:.0%} off its 52-week high. Correlation with SPY is "
            f"{spy_correlation:.2f}, so the dip may mix market pressure with stock-specific drift."
        )

    if hold_days < 45:
        horizon_note = (
            "The hold window is still measured in weeks, not days, but it is short enough "
            "that the sell target leans on a partial mean-reversion rather than a full recovery."
        )
    elif hold_days < 180:
        horizon_note = (
            "On a multi-month horizon the sell target assumes the stock recaptures a meaningful "
            "slice of the drawdown if the business stays intact."
        )
    else:
        horizon_note = (
            "The longer hold window lets the sell target assume a deeper recovery toward the "
            "prior high, still capped so the number stays realistic."
        )

    research = ""
    if fund.research_note:
        research = f"**SEC research.** {fund.research_note}\n\n"

    return (
        f"### {fund.name} ({snapshot.ticker}) — confidence {confidence:.0f}/100\n\n"
        f"{research}"
        f"**Well-run check (quality {quality:.0f}/100).** "
        f"{fund.name} still screens as an established operator in {fund.sector.lower()}: "
        f"ROE {roe_text}, {fcf_text}, {growth_text}, and {debt_text}.\n\n"
        f"**Macro suppression (dip {macro:.0f}/100).** {macro_reason}\n\n"
        f"**Levels for a {hold_days}-day hold.** Buy-in **${buy_in:,.2f}** and sell-out "
        f"**${sell_out:,.2f}** imply about **{expected:.1f}%** if the thesis plays out. "
        f"{horizon_note}\n\n"
        f"**Risks.** A deeper recession, a genuine company-specific miss, or a market that "
        f"stays risk-off longer than {hold_days} days can keep the stock below the sell target. "
        "This is a screen, not a recommendation to buy or sell."
    )


def to_opportunity(
    snapshot: Snapshot,
    *,
    buy_in: float,
    sell_out: float,
    hold_days: int,
    quality: float,
    macro: float,
    confidence: float,
    drawdown_pct: float,
    spy_correlation: float,
    market_drawdown: float,
) -> Opportunity:
    return Opportunity(
        ticker=snapshot.ticker,
        name=snapshot.fundamentals.name,
        sector=snapshot.fundamentals.sector,
        current_price=round(snapshot.current_price, 2),
        buy_in=buy_in,
        sell_out=sell_out,
        hold_days=hold_days,
        expected_return_pct=round((sell_out - buy_in) / buy_in * 100.0, 1),
        confidence=round(confidence, 1),
        quality_score=round(quality, 1),
        macro_score=round(macro, 1),
        analysis=build_analysis(
            snapshot,
            buy_in=buy_in,
            sell_out=sell_out,
            hold_days=hold_days,
            quality=quality,
            macro=macro,
            confidence=confidence,
            drawdown_pct=drawdown_pct,
            spy_correlation=spy_correlation,
            market_drawdown=market_drawdown,
        ),
        drawdown_pct=round(drawdown_pct * 100.0, 1),
        spy_correlation=round(spy_correlation, 2),
        pe_ratio=snapshot.fundamentals.trailing_pe,
        roe=snapshot.fundamentals.roe,
        extras={
            "source": snapshot.fundamentals.source,
            "research_note": snapshot.fundamentals.research_note,
        },
    )
