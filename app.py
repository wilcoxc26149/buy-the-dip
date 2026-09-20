from __future__ import annotations

import os
from datetime import datetime, timezone

import gradio as gr
import pandas as pd

from src.screener import ScreenError, screen_detailed
from src.universe import (
    DEFAULT_COMPANIES,
    DEFAULT_HOLD_DAYS,
    DEFAULT_MAX_PRICE,
    MAX_COMPANIES,
    MAX_HOLD_DAYS,
    MIN_COMPANIES,
    MIN_HOLD_DAYS,
)

DISCLAIMER = (
    "Educational screen only — not investment advice, an offer, or a solicitation. "
    "Markets can stay wrong longer than a hold window, and past recovery patterns "
    "do not forecast future prices."
)

THEME = gr.themes.Soft(primary_hue="emerald", secondary_hue="slate", neutral_hue="slate")
CSS = """
.hero-sub { font-size: 1.05rem; line-height: 1.45; }
.disclaimer { font-size: 0.92rem; opacity: 0.88; }
#find-dips-btn button { font-weight: 650; }
"""


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "Ticker",
            "Company",
            "Sector",
            "Current",
            "Buy-in",
            "Sell-out",
            "Hold (days)",
            "Expected return",
            "Confidence",
            "Quality",
            "Macro dip",
        ]
    )


def _empty_reason(result) -> str:
    if result.scanned == 0:
        return (
            "No market data came back for the quality universe. "
            "Yahoo Finance may be rate-limiting this session — wait a minute and try again."
        )
    if result.priced_out and result.priced_out == result.scanned:
        cheapest = ""
        if result.cheapest_over_max:
            ticker, price = result.cheapest_over_max
            cheapest = f" The cheapest screened name is **{ticker} at ${price:,.2f}**."
        return (
            f"Every name in the universe trades above your max quote price."
            f"{cheapest} Raise the max quote price and run the screen again."
        )
    return (
        f"Scanned {result.scanned} companies: {result.priced_out} were over the max quote price "
        f"and {result.quality_rejected} failed the well-run check. "
        "Raise the max quote price to include more of the quality universe."
    )


def run_screen(max_quote_price, hold_days, company_count, progress=gr.Progress()):
    progress(0.15, desc="Loading market data")
    try:
        result = screen_detailed(max_quote_price, hold_days, company_count)
        opportunities = result.opportunities
    except ScreenError as exc:
        return _empty_frame(), f"**Could not run the screen.** {exc}", f"Status: {exc}"
    except Exception as exc:  # noqa: BLE001
        return _empty_frame(), f"**Data error.** {exc}", f"Status: failed ({exc})"

    progress(0.8, desc="Scoring companies")
    if not opportunities:
        return _empty_frame(), _empty_reason(result), "Status: 0 companies matched"

    rows = [
        {
            "Ticker": item.ticker,
            "Company": item.name,
            "Sector": item.sector,
            "Current": f"${item.current_price:,.2f}",
            "Buy-in": f"${item.buy_in:,.2f}",
            "Sell-out": f"${item.sell_out:,.2f}",
            "Hold (days)": item.hold_days,
            "Expected return": f"{item.expected_return_pct:.1f}%",
            "Confidence": f"{item.confidence:.0f}/100",
            "Quality": f"{item.quality_score:.0f}",
            "Macro dip": f"{item.macro_score:.0f}",
        }
        for item in opportunities
    ]
    preface = ""
    if result.grade is not None:
        preface += result.grade.as_markdown() + "\n\n"
    if result.shallow_backfill:
        preface += (
            f"_The tape is not offering a deep pullback for every slot. "
            f"{result.shallow_backfill} of these names are less than 3% off their 52-week high, "
            "so confidence is lower than a true macro dip._\n\n"
        )
    analysis = preface + "\n\n---\n\n".join(item.analysis for item in opportunities)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    letter = result.grade.letter if result.grade is not None else "n/a"
    status = (
        f"Status: {len(opportunities)} companies · grade {letter} · scanned {result.scanned} · "
        f"{result.priced_out} over max price · updated {stamp}"
    )
    progress(1.0, desc="Done")
    return pd.DataFrame(rows), analysis, status


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Leeward") as demo:
        gr.Markdown("# Leeward")
        gr.Markdown(
            "Find **well-run public companies** on the sheltered side of a macro storm, "
            "then set a **buy-in** and a **sell-out** for a hold measured in days — "
            "not minutes.",
            elem_classes=["hero-sub"],
        )
        gr.Markdown(DISCLAIMER, elem_classes=["disclaimer"])

        with gr.Row():
            max_quote = gr.Number(
                label="Max quote price ($)",
                value=DEFAULT_MAX_PRICE,
                minimum=5,
                maximum=2500,
                elem_id="max-quote-price",
            )
            hold_days = gr.Slider(
                label="Days until you intend to sell",
                minimum=MIN_HOLD_DAYS,
                maximum=MAX_HOLD_DAYS,
                value=DEFAULT_HOLD_DAYS,
                step=1,
                elem_id="hold-days",
            )
            company_count = gr.Slider(
                label="Companies to return",
                minimum=MIN_COMPANIES,
                maximum=MAX_COMPANIES,
                value=DEFAULT_COMPANIES,
                step=1,
                elem_id="company-count",
            )

        find_btn = gr.Button("Find leeward names", variant="primary", elem_id="find-dips-btn")
        status = gr.Markdown("Status: waiting for a screen", elem_id="status-output")
        results = gr.Dataframe(label="Ranked opportunities", elem_id="results-table", wrap=True)
        analysis = gr.Markdown(
            "Analysis and confidence notes will appear here.",
            elem_id="analysis-output",
        )

        gr.Examples(
            examples=[
                [250, 90, 5],
                [100, 180, 5],
                [500, 90, 8],
            ],
            inputs=[max_quote, hold_days, company_count],
            label="Example screens",
        )

        find_btn.click(
            fn=run_screen,
            inputs=[max_quote, hold_days, company_count],
            outputs=[results, analysis, status],
        )

    return demo


demo = build_demo()


def launch_app(**kwargs):
    params = {
        "theme": THEME,
        "css": CSS,
        "server_name": os.environ.get("GRADIO_SERVER_NAME"),
        "server_port": int(os.environ["GRADIO_SERVER_PORT"]) if os.environ.get("GRADIO_SERVER_PORT") else None,
    }
    params.update(kwargs)
    return demo.launch(**{key: value for key, value in params.items() if value is not None})


if __name__ == "__main__":
    launch_app()
