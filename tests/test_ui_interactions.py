import time
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from windforecast.render import ReportRenderer


def create_minimal_test_data():
    """Create minimal test data for UI tests."""
    return {
        "spots": [
            {
                "spot": "Test Spot",
                "rows": [
                    {
                        "time": "2025-10-23T12:00:00Z",
                        "wind_kn": 20,
                        "gust_kn": 25,
                        "dir": "N",
                        "dir_deg": 0,
                        "wave_m": 1.5,
                        "precip_mm_h": 0,
                        "kiteable": True,
                    }
                ],
            }
        ],
        "config": {
            "spots": [
                {
                    "name": "Test Spot",
                    "lat": 41.3948,
                    "lon": 2.2105,
                    "dir_sector": {"start": 225, "end": 45, "wrap": True},
                }
            ],
            "forecast": {
                "model": "arome_france_hd",
                "hourly_vars": "wind_speed_10m,wind_direction_10m",
                "wave_vars": "wave_height",
                "forecast_hours_hourly": 48,
                "forecast_min15": 24,
            },
            "time_window": {"day_start": 6, "day_end": 20},
            "conditions": {
                "bands": [["too much", 30], ["good", 15], ["light", 10], ["below", 0]],
                "rain_limit": 0.5,
            },
        },
        "generated_at": "2025-10-23T12:00:00Z",
    }


def test_daily_summary_initial_state(tmp_path):
    """Test that the daily summary is initially hidden with correct HTML structure."""
    renderer = ReportRenderer()
    report_path = tmp_path / "test_report.html"
    renderer.render_html(create_minimal_test_data(), report_path)

    soup = BeautifulSoup(report_path.read_text(), "html.parser")

    # Verify toggle button exists with correct initial text
    toggle_button = soup.find("button", id="toggleSummary")
    assert (
        toggle_button and toggle_button.string == "Show Daily Summary"
    ), "Toggle button should exist with 'Show Daily Summary' text"

    # Verify initial hidden state
    body = soup.find("body")
    assert body.get("data-show-summary") == "false", "Daily summary should be hidden by default"

    # Verify JavaScript includes necessary toggle function
    js_content = "\n".join(script.string for script in soup.find_all("script") if script.string)
    assert "function toggleDailySummary()" in js_content, "JavaScript should have toggle function"
    assert (
        "showDailySummary ? 'true' : 'false'" in js_content
    ), "JavaScript should toggle data-show-summary"


def test_daily_summary_interaction(tmp_path):
    """Test that clicking the button shows/hides the summary using Selenium."""
    renderer = ReportRenderer()
    report_path = tmp_path / "test_report.html"
    renderer.render_html(create_minimal_test_data(), report_path)

    # Verify daily summary element exists
    soup = BeautifulSoup(report_path.read_text(), "html.parser")
    assert soup.find(class_="daily-summary"), "Daily summary element should exist in the HTML"

    # Set up Chrome in headless mode
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(f"file://{report_path.absolute()}")
        wait = WebDriverWait(driver, 10)

        # Get elements
        toggle_button = wait.until(EC.presence_of_element_located((By.ID, "toggleSummary")))
        daily_summary = driver.find_element(By.CLASS_NAME, "daily-summary")
        body = driver.find_element(By.TAG_NAME, "body")

        # Check initial state
        assert not daily_summary.is_displayed(), "Daily summary should be hidden initially"
        assert body.get_attribute("data-show-summary") == "false"

        # Click to show
        toggle_button.click()
        wait.until(EC.visibility_of(daily_summary))
        assert daily_summary.is_displayed(), "Daily summary should be visible after click"
        assert body.get_attribute("data-show-summary") == "true"
        assert toggle_button.text == "Hide Daily Summary"

        # Click to hide
        toggle_button.click()
        wait.until(EC.invisibility_of_element(daily_summary))
        assert not daily_summary.is_displayed(), "Daily summary should be hidden after second click"
        assert body.get_attribute("data-show-summary") == "false"
        assert toggle_button.text == "Show Daily Summary"

    finally:
        driver.quit()
