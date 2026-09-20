from __future__ import annotations

import os
from datetime import datetime, timezone

import gradio as gr
import pandas as pd

from src.screener import ScreenError, screen
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


def run_screen(max_quote_price, hold_days, company_count, progress=gr.Progress()):
    progress(0.15, desc="Loading market data")
    try:
        opportunities = screen(max_quote_price, hold_days, company_count)
    except ScreenError as exc:
        empty = pd.DataFrame(
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
        return empty, f"**Could not run the screen.** {exc}", f"Status: {exc}"
    except Exception as exc:  # noqa: BLE001
        empty = pd.DataFrame()
        return empty, f"**Data error.** {exc}", f"Status: failed ({exc})"

    progress(0.8, desc="Scoring companies")
    if not opportunities:
        return (
            pd.DataFrame(),
            "No names cleared the quality, macro-dip, and max-price filters. "
            "Raise the max quote price or lengthen the hold window and try again.",
            "Status: 0 companies matched",
        )

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
    analysis = "\n\n---\n\n".join(item.analysis for item in opportunities)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status = f"Status: {len(opportunities)} companies · updated {stamp}"
    progress(1.0, desc="Done")
    return pd.DataFrame(rows), analysis, status


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Buy the Dip") as demo:
        gr.Markdown("# Buy the Dip")
        gr.Markdown(
            "Find **well-run public companies** whose prices look suppressed by the "
            "macro tape, then set a **buy-in** and a **sell-out** for a hold measured "
            "in days — not minutes.",
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

        find_btn = gr.Button("Find dip opportunities", variant="primary", elem_id="find-dips-btn")
        status = gr.Markdown("Status: waiting for a screen", elem_id="status-output")
        results = gr.Dataframe(label="Ranked opportunities", elem_id="results-table", wrap=True)
        analysis = gr.Markdown(
            "Analysis and confidence notes will appear here.",
            elem_id="analysis-output",
        )

        gr.Examples(
            examples=[
                [150, 90, 5],
                [80, 180, 8],
                [400, 60, 5],
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
