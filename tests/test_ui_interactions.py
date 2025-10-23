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


def test_daily_summary_initial_state(tmp_path):
    """Test that the daily summary is initially hidden"""
    test_data = {
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

    renderer = ReportRenderer()
    report_path = tmp_path / "test_report.html"
    renderer.render_html(test_data, report_path)

    # Read the generated HTML
    html_content = report_path.read_text()
    soup = BeautifulSoup(html_content, "html.parser")

    # Check initial button state
    toggle_button = soup.find("button", id="toggleSummary")
    assert toggle_button is not None, "Toggle button should exist"
    assert (
        toggle_button.string == "Show Daily Summary"
    ), 'Initial button text should be "Show Daily Summary"'

    # Check initial body attribute
    body = soup.find("body")
    assert "data-show-summary" in body.attrs, "Body should have data-show-summary attribute"
    assert body["data-show-summary"] == "false", "Daily summary should be hidden by default"

    # Check CSS rules for daily summary visibility
    style_tags = soup.find_all("style")
    css_content = "\n".join(style.string for style in style_tags if style.string)

    # Check for necessary JavaScript functionality
    scripts = soup.find_all("script")
    js_content = "\n".join(script.string for script in scripts if script.string)
    assert "function toggleDailySummary()" in js_content, "JavaScript should have toggle function"
    assert (
        "body.setAttribute('data-show-summary', 'false')" in js_content
    ), "JavaScript should set data-show-summary attribute to false"
    assert (
        "showDailySummary ? 'true' : 'false'" in js_content
    ), "JavaScript should properly toggle data-show-summary value"


def test_daily_summary_interaction(tmp_path):
    """Test that clicking the button shows/hides the summary"""
    test_data = {
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

    renderer = ReportRenderer()
    report_path = tmp_path / "test_report.html"
    renderer.render_html(test_data, report_path)

    # Print the generated HTML for debugging
    html_content = report_path.read_text()
    print(f"\nGenerated HTML for {report_path}:")
    print(html_content)

    # Check if daily summary is in the HTML
    soup = BeautifulSoup(html_content, "html.parser")
    daily_summary = soup.find(class_="daily-summary")
    assert daily_summary is not None, "Daily summary element should exist in the HTML"

    # Set up Chrome in headless mode
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Initialize the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # Load the page
        driver.get(f"file://{report_path.absolute()}")

        # Wait for the toggle button to be present
        wait = WebDriverWait(driver, 10)
        toggle_button = wait.until(EC.presence_of_element_located((By.ID, "toggleSummary")))

        # Check initial state
        daily_summary = driver.find_element(By.CLASS_NAME, "daily-summary")
        assert not daily_summary.is_displayed(), "Daily summary should be hidden initially"
        assert (
            driver.find_element(By.TAG_NAME, "body").get_attribute("data-show-summary") == "false"
        )

        # Click the button
        toggle_button.click()
        time.sleep(0.5)  # Give the browser a moment to update

        # Check state after click
        assert (
            daily_summary.is_displayed()
        ), "Daily summary should be visible after clicking the button"
        assert driver.find_element(By.TAG_NAME, "body").get_attribute("data-show-summary") == "true"
        assert toggle_button.text == "Hide Daily Summary"

        # Click again to hide
        toggle_button.click()
        time.sleep(0.5)  # Give the browser a moment to update

        # Check state after second click
        assert (
            not daily_summary.is_displayed()
        ), "Daily summary should be hidden after clicking again"
        assert (
            driver.find_element(By.TAG_NAME, "body").get_attribute("data-show-summary") == "false"
        )
        assert toggle_button.text == "Show Daily Summary"

    finally:
        driver.quit()
