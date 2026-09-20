from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.ciks import TICKER_CIKS, cik_for
from src.httputil import SEC_USER_AGENT, get_json
from src.models import Fundamentals
from src.universe import SECTORS

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

logger = logging.getLogger(__name__)

_SEC_HEADERS = {"User-Agent": SEC_USER_AGENT, "Accept": "application/json"}

REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)
INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic")
OPERATING_TAGS = ("OperatingIncomeLoss",)
EQUITY_TAGS = (
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
)
ASSET_TAGS = ("Assets",)
CURRENT_ASSET_TAGS = ("AssetsCurrent",)
LIABILITY_TAGS = ("Liabilities",)
CURRENT_LIABILITY_TAGS = ("LiabilitiesCurrent",)
DEBT_TAGS = ("LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations")
CFO_TAGS = ("NetCashProvidedByUsedInOperatingActivities",)
CAPEX_TAGS = ("PaymentsToAcquirePropertyPlantAndEquipment",)
EPS_TAGS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")

def load_research_fundamentals(tickers: list[str]) -> dict[str, Fundamentals]:
    """SEC companyfacts first; Finnhub or Alpha Vantage only fill gaps."""
    results = load_sec_fundamentals(tickers)
    missing = [ticker for ticker in tickers if ticker not in results]
    if missing:
        from src.vendors import load_vendor_fundamentals

        results.update(load_vendor_fundamentals(missing))
    return results


def load_sec_fundamentals(tickers: list[str]) -> dict[str, Fundamentals]:
    results: dict[str, Fundamentals] = {}

    def _one(ticker: str) -> tuple[str, Fundamentals | None]:
        cik = cik_for(ticker)
        if not cik:
            return ticker, None
        payload = get_json(COMPANYFACTS_URL.format(cik=cik), headers=_SEC_HEADERS, timeout=30)
        return ticker, fundamentals_from_companyfacts(ticker, payload)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_one, ticker) for ticker in tickers]
        for future in as_completed(futures):
            try:
                ticker, fundamentals = future.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning("SEC companyfacts failed: %s", exc)
                continue
            if fundamentals is not None:
                results[ticker] = fundamentals
    return results


def load_ticker_ciks() -> dict[str, str]:
    return dict(TICKER_CIKS)


def fundamentals_from_companyfacts(ticker: str, payload: dict) -> Fundamentals:
    gaap = ((payload.get("facts") or {}).get("us-gaap") or {})
    name = str(payload.get("entityName") or ticker)
    revenue = _latest_annual(gaap, REVENUE_TAGS)
    income = _latest_annual(gaap, INCOME_TAGS)
    prior_income = _prior_annual(gaap, INCOME_TAGS)
    operating = _latest_annual(gaap, OPERATING_TAGS)
    equity = _latest_annual(gaap, EQUITY_TAGS)
    assets = _latest_annual(gaap, ASSET_TAGS)
    current_assets = _latest_annual(gaap, CURRENT_ASSET_TAGS)
    liabilities = _latest_annual(gaap, LIABILITY_TAGS)
    current_liabilities = _latest_annual(gaap, CURRENT_LIABILITY_TAGS)
    debt = _latest_annual(gaap, DEBT_TAGS)
    cfo = _latest_annual(gaap, CFO_TAGS)
    capex = _latest_annual(gaap, CAPEX_TAGS)
    eps = _latest_annual(gaap, EPS_TAGS, units=("USD/shares", "USD"))

    roe = _ratio(income, equity)
    operating_margin = _ratio(operating, revenue)
    profit_margin = _ratio(income, revenue)
    debt_to_equity = _ratio(debt if debt is not None else liabilities, equity)
    if debt_to_equity is not None:
        debt_to_equity *= 100.0
    current_ratio = _ratio(current_assets, current_liabilities)
    free_cash_flow = None
    if cfo is not None:
        free_cash_flow = cfo - abs(capex or 0.0)
    earnings_growth = None
    if income is not None and prior_income not in (None, 0):
        earnings_growth = (income - prior_income) / abs(prior_income)

    note = _research_note(name, income, roe, operating_margin)
    return Fundamentals(
        name=name,
        sector=SECTORS.get(ticker, "Unknown"),
        roe=roe,
        operating_margin=operating_margin,
        profit_margin=profit_margin,
        debt_to_equity=debt_to_equity,
        current_ratio=current_ratio,
        free_cash_flow=free_cash_flow,
        earnings_growth=earnings_growth,
        trailing_pe=None,
        return_on_assets=_ratio(income, assets),
        source="SEC EDGAR companyfacts",
        research_note=note,
    )


def _latest_annual(gaap: dict, tags: tuple[str, ...], units: tuple[str, ...] = ("USD",)) -> float | None:
    rows = _annual_rows(gaap, tags, units)
    return rows[-1] if rows else None


def _prior_annual(gaap: dict, tags: tuple[str, ...], units: tuple[str, ...] = ("USD",)) -> float | None:
    rows = _annual_rows(gaap, tags, units)
    return rows[-2] if len(rows) >= 2 else None


def _annual_rows(gaap: dict, tags: tuple[str, ...], units: tuple[str, ...]) -> list[float]:
    for tag in tags:
        concept = gaap.get(tag) or {}
        values = []
        for unit in units:
            values.extend((concept.get("units") or {}).get(unit) or [])
        annual = [
            row
            for row in values
            if row.get("val") is not None
            and row.get("end")
            and (row.get("form") in {"10-K", "20-F", "40-F"} or row.get("fp") == "FY")
        ]
        if not annual:
            continue
        annual.sort(key=lambda row: row["end"])
        # One value per fiscal year, last filing wins.
        by_year: dict[str, float] = {}
        for row in annual:
            by_year[str(row.get("fy") or row["end"][:4])] = float(row["val"])
        return [by_year[year] for year in sorted(by_year)]
    return []


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or not denominator:
        return None
    return numerator / denominator


def _research_note(name: str, income: float | None, roe: float | None, operating_margin: float | None) -> str:
    parts = [f"SEC 10-K research for {name}"]
    if income is not None:
        parts.append(f"latest annual net income ${_format_money(income)}")
    if roe is not None:
        parts.append(f"ROE {roe:.0%}")
    if operating_margin is not None:
        parts.append(f"operating margin {operating_margin:.0%}")
    return "; ".join(parts) + "."


def _format_money(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    return f"{value:,.0f}"
