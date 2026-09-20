from __future__ import annotations

from src.prices import parse_chart_payload
from src.research import fundamentals_from_companyfacts


def test_parse_chart_payload_reads_closes_and_highs():
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"regularMarketPrice": 101.5, "fiftyTwoWeekHigh": 120.0},
                    "indicators": {
                        "quote": [
                            {
                                "close": [90 + i * 0.2 for i in range(40)],
                                "high": [91 + i * 0.2 for i in range(40)],
                            }
                        ]
                    },
                }
            ]
        }
    }
    history, current, high_52w = parse_chart_payload(payload)
    assert current == 101.5
    assert high_52w == 120.0
    assert len(history.close) == 40
    assert history.close[0] == 90


def test_companyfacts_builds_research_fundamentals():
    payload = {
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-09-30", "val": 380_000_000_000},
                            {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-09-28", "val": 390_000_000_000},
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-09-30", "val": 90_000_000_000},
                            {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-09-28", "val": 99_000_000_000},
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-09-28", "val": 120_000_000_000},
                        ]
                    }
                },
                "StockholdersEquity": {
                    "units": {
                        "USD": [
                            {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-09-28", "val": 60_000_000_000},
                        ]
                    }
                },
                "AssetsCurrent": {
                    "units": {
                        "USD": [
                            {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-09-28", "val": 140_000_000_000},
                        ]
                    }
                },
                "LiabilitiesCurrent": {
                    "units": {
                        "USD": [
                            {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-09-28", "val": 140_000_000_000},
                        ]
                    }
                },
                "LongTermDebt": {
                    "units": {
                        "USD": [
                            {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-09-28", "val": 90_000_000_000},
                        ]
                    }
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-09-28", "val": 110_000_000_000},
                        ]
                    }
                },
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {
                        "USD": [
                            {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-09-28", "val": 10_000_000_000},
                        ]
                    }
                },
            }
        },
    }
    fundamentals = fundamentals_from_companyfacts("AAPL", payload)
    assert fundamentals.name == "Apple Inc."
    assert fundamentals.source == "SEC EDGAR companyfacts"
    assert fundamentals.roe == 99_000_000_000 / 60_000_000_000
    assert fundamentals.operating_margin == 120_000_000_000 / 390_000_000_000
    assert fundamentals.free_cash_flow == 100_000_000_000
    assert fundamentals.earnings_growth == 0.1
    assert "SEC 10-K research" in (fundamentals.research_note or "")
