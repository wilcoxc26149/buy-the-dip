from __future__ import annotations

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_home_page_renders_controls(page, app_url):
    page.goto(app_url, wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Buy the Dip")).to_be_visible()
    expect(page.locator("#max-quote-price")).to_be_visible()
    expect(page.locator("#hold-days")).to_be_visible()
    expect(page.locator("#company-count")).to_be_visible()
    expect(page.get_by_role("button", name="Find dip opportunities")).to_be_visible()


@pytest.mark.e2e
def test_screen_returns_analysis_and_levels(page, app_url):
    page.goto(app_url, wait_until="networkidle")
    page.get_by_role("button", name="Find dip opportunities").click()
    expect(page.locator("#status-output")).to_contain_text("companies", timeout=45_000)
    expect(page.locator("#analysis-output")).to_contain_text("Buy-in")
    expect(page.locator("#analysis-output")).to_contain_text("sell-out")
    expect(page.locator("#analysis-output")).to_contain_text("confidence")
    expect(page.locator("#results-table")).to_contain_text("Ticker")


@pytest.mark.e2e
def test_max_price_and_company_count_are_honored(page, app_url):
    page.goto(app_url, wait_until="networkidle")
    price_box = page.locator("#max-quote-price input").last
    price_box.fill("80")
    page.get_by_role("button", name="Find dip opportunities").click()
    expect(page.locator("#status-output")).to_contain_text("companies", timeout=45_000)
    expect(page.locator("#analysis-output")).to_contain_text("confidence")
