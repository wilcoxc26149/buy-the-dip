---
title: Leeward
emoji: ⛵
colorFrom: green
colorTo: gray
sdk: gradio
sdk_version: 6.28.0
app_file: app.py
python_version: "3.12"
pinned: false
license: mit
short_description: Quality companies on the cheap side of the tape
tags:
  - finance
  - stocks
  - gradio
---

# Leeward

A Hugging Face Gradio app that looks for **well-run public companies** on the **sheltered side of a macro storm**, then returns:

- a **buy-in** price
- a **sell-out** price for the hold window you choose
- a short **analysis** and **confidence score**

This is a screen, not a broker and not investment advice.

## What you control

| Control | Meaning |
| --- | --- |
| Max quote price | Ignore names trading above this dollar amount. Default is $500 so large-cap quality names are not excluded by share price alone |
| Days until you intend to sell | Hold window in days (14–365). The minimum is 14 on purpose — this is not a day-trading tool |
| Companies to return | How many ranked names to show (1–12) |

## How the screen thinks

1. Start from a quality-biased universe of liquid public companies.
2. Keep names at or under your max quote price.
3. Score **quality** from profitability, leverage, cash flow, and growth.
4. Score **macro suppression** from drawdown versus the 52-week high, correlation with SPY, and whether the stock is below its long moving average while earnings still look intact.
5. Set **buy-in** near current/support if the dip is already here.
6. Set **sell-out** from a time-scaled recovery toward the prior high, capped so a 30-day hold cannot promise a full bounce-back.
7. Rank by confidence, expected return, and quality.

Live runs use public research endpoints, not Yahoo's company-info scrape:

- **Prices:** Yahoo's public chart API (`query1.finance.yahoo.com/v8/finance/chart`)
- **Fundamentals:** [SEC EDGAR companyfacts](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) via a **local ticker → CIK map** in `src/ciks.py` (the SEC ticker-file endpoint 403s from many IPs)
- **Optional fill-in:** `FINNHUB_API_KEY` and/or `ALPHA_VANTAGE_API_KEY` only for names SEC misses

Each screen also gets an **overall grade** (A–F) for quality, dip authenticity, research coverage, levels, confidence, and sector mix.

Set `MARKET_DATA_PROVIDER=yahoo` to force the older `yfinance` path. Jenkins and Playwright use deterministic fixture data (`USE_MOCK_DATA=1`) so CI does not depend on those endpoints.

## Run locally

```powershell
cd c:\Users\wilco\projects\buy-the-dip
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python app.py
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860).

To develop against fixture data instead of Yahoo Finance:

```powershell
$env:USE_MOCK_DATA = "1"
python app.py
```

## Hugging Face Space

The repo root is Space-ready: `README.md` frontmatter + `app.py` + `requirements.txt`.

1. Create a Gradio Space on [huggingface.co/new-space](https://huggingface.co/new-space).
2. Push this repository to the Space, or connect the GitHub repo in the Space settings.
3. After it builds, Playwright can target the Space URL:

```powershell
$env:BASE_URL = "https://YOUR-SPACE.hf.space"
python -m pytest tests/e2e
```

## Playwright

```powershell
pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest tests/unit
python -m pytest tests/e2e
```

`tests/e2e` launches the local Gradio app with mock data unless `BASE_URL` is set.

## Jenkins

The `Jenkinsfile` is a Pipeline job:

1. Install Jenkins plus the **Pipeline**, **Git**, and **JUnit** plugins.
2. New item → Pipeline → Pipeline script from SCM → Git → this repository → `Jenkinsfile` on `main`.
3. Add a GitHub webhook or poll SCM.
4. The job installs dependencies, runs unit tests, installs Chromium, then runs Playwright. Reports land in `reports/`.

Local stand-in for the same flow:

```powershell
powershell -File ci\run-tests.ps1
```

On Linux/macOS:

```bash
bash ci/run-tests.sh
```

## Disclaimer

Nothing here is a recommendation to buy, sell, or hold any security. Do your own research.
