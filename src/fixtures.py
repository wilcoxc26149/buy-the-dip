from __future__ import annotations

import numpy as np

from src.models import Fundamentals, PriceHistory, Snapshot
from src.universe import MARKET_TICKER


def _to_history(closes: np.ndarray) -> PriceHistory:
    highs = np.maximum(closes, np.roll(closes, 1)) * 1.008
    highs[0] = closes[0] * 1.01
    return PriceHistory(close=[float(x) for x in closes], high=[float(x) for x in highs])


def _spy_path(n: int = 252, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    drift = np.concatenate([np.full(100, 0.0007), np.full(n - 100, -0.00115)])
    rets = drift + rng.normal(0.0, 0.0075, n)
    return 520.0 * np.cumprod(1.0 + rets)


def _beta_path(spy: np.ndarray, start: float, beta: float, idio: float, seed: int) -> np.ndarray:
    spy_rets = np.zeros_like(spy)
    spy_rets[1:] = (spy[1:] - spy[:-1]) / spy[:-1]
    rng = np.random.default_rng(seed)
    rets = beta * spy_rets + rng.normal(0.0, idio, len(spy))
    prices = start * np.cumprod(1.0 + rets)
    prices[0] = start
    return prices


def _quality(**overrides) -> Fundamentals:
    base = dict(
        sector="Technology",
        roe=0.26,
        operating_margin=0.21,
        profit_margin=0.17,
        debt_to_equity=48.0,
        current_ratio=1.55,
        free_cash_flow=8_000_000_000,
        earnings_growth=0.11,
        trailing_pe=27.0,
        return_on_assets=0.12,
    )
    base.update(overrides)
    name = base.pop("name")
    sector = base.pop("sector")
    return Fundamentals(name=name, sector=sector, **base)


class FixtureProvider:
    """Deterministic market data so unit tests, Playwright, and Jenkins stay offline."""

    def load(self, tickers: tuple[str, ...] | None = None) -> tuple[list[Snapshot], PriceHistory]:
        spy = _spy_path()
        catalog = self._catalog(spy)
        selected = catalog
        if tickers:
            wanted = set(tickers) | {MARKET_TICKER}
            selected = [item for item in catalog if item.ticker in wanted]
        return selected, _to_history(spy)

    def _catalog(self, spy: np.ndarray) -> list[Snapshot]:
        specs: list[tuple[str, Fundamentals, np.ndarray]] = [
            (
                "AAPL",
                _quality(name="Apple Inc.", sector="Technology", roe=0.46, trailing_pe=32.0),
                _beta_path(spy, 228.0, beta=1.05, idio=0.0035, seed=11),
            ),
            (
                "JPM",
                _quality(
                    name="JPMorgan Chase",
                    sector="Financial Services",
                    roe=0.17,
                    operating_margin=0.38,
                    debt_to_equity=95.0,
                    trailing_pe=13.0,
                ),
                _beta_path(spy, 198.0, beta=1.15, idio=0.004, seed=12),
            ),
            (
                "HD",
                _quality(name="Home Depot", sector="Consumer Cyclical", roe=0.64, trailing_pe=24.0),
                _beta_path(spy, 368.0, beta=0.95, idio=0.0038, seed=13),
            ),
            (
                "CAT",
                _quality(name="Caterpillar", sector="Industrials", roe=0.48, trailing_pe=16.0),
                _beta_path(spy, 312.0, beta=1.20, idio=0.0045, seed=14),
            ),
            (
                "V",
                _quality(name="Visa Inc.", sector="Financial Services", roe=0.45, trailing_pe=29.0),
                _beta_path(spy, 278.0, beta=0.92, idio=0.003, seed=15),
            ),
            (
                "NEE",
                _quality(
                    name="NextEra Energy",
                    sector="Utilities",
                    roe=0.12,
                    operating_margin=0.28,
                    trailing_pe=21.0,
                ),
                _beta_path(spy, 78.0, beta=0.70, idio=0.0032, seed=16),
            ),
            (
                "XOM",
                _quality(
                    name="Exxon Mobil",
                    sector="Energy",
                    roe=0.16,
                    operating_margin=0.14,
                    trailing_pe=13.5,
                    debt_to_equity=20.0,
                ),
                _beta_path(spy, 118.0, beta=0.85, idio=0.005, seed=17),
            ),
            (
                "PG",
                _quality(name="Procter & Gamble", sector="Consumer Defensive", roe=0.30, trailing_pe=26.0),
                _beta_path(spy, 168.0, beta=0.55, idio=0.0028, seed=18),
            ),
            (
                "KO",
                _quality(name="Coca-Cola", sector="Consumer Defensive", roe=0.38, trailing_pe=24.0),
                _beta_path(spy, 64.0, beta=0.50, idio=0.0025, seed=19),
            ),
            (
                "MSFT",
                _quality(name="Microsoft", sector="Technology", roe=0.35, trailing_pe=34.0),
                _beta_path(spy, 420.0, beta=1.08, idio=0.0032, seed=20),
            ),
            (
                "COST",
                _quality(name="Costco", sector="Consumer Defensive", roe=0.28, trailing_pe=50.0),
                _beta_path(spy, 890.0, beta=0.80, idio=0.003, seed=21),
            ),
            (
                "JUNK",
                Fundamentals(
                    name="Broken Biz Inc.",
                    sector="Unknown",
                    roe=0.01,
                    operating_margin=-0.04,
                    profit_margin=-0.08,
                    debt_to_equity=340.0,
                    current_ratio=0.6,
                    free_cash_flow=-80_000_000,
                    earnings_growth=-0.45,
                    trailing_pe=None,
                    return_on_assets=-0.03,
                ),
                _collapse_path(spy, 28.0, seed=90),
            ),
            (
                "NODIP",
                _quality(name="All Time High Co.", sector="Technology", roe=0.22),
                _melt_up_path(spy, 142.0, seed=91),
            ),
        ]
        snapshots = []
        for ticker, fundamentals, closes in specs:
            history = _to_history(closes)
            snapshots.append(
                Snapshot(
                    ticker=ticker,
                    fundamentals=fundamentals,
                    prices=history,
                    current_price=round(history.close[-1], 2),
                    high_52w=round(max(history.high), 2),
                )
            )
        return snapshots


def _collapse_path(spy: np.ndarray, start: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    spy_rets = np.zeros_like(spy)
    spy_rets[1:] = (spy[1:] - spy[:-1]) / spy[:-1]
    shock = np.concatenate([np.zeros(160), np.full(len(spy) - 160, -0.012)])
    rets = 0.15 * spy_rets + rng.normal(0.0, 0.02, len(spy)) + shock
    prices = start * np.cumprod(1.0 + rets)
    prices[0] = start
    return prices


def _melt_up_path(spy: np.ndarray, start: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    spy_rets = np.zeros_like(spy)
    spy_rets[1:] = (spy[1:] - spy[:-1]) / spy[:-1]
    rets = 0.15 * spy_rets + rng.normal(0.0, 0.003, len(spy)) + 0.0014
    prices = start * np.cumprod(1.0 + rets)
    prices[0] = start
    return prices
