"""Tests for expanded view and search functionality in HTML reports."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from windforecast.render import ReportRenderer
from windforecast.schemas import WindConfig


def test_expanded_view_controls():
    """Test that expanded view controls are present in the HTML."""
    renderer = ReportRenderer()

    # Create minimal test data
    data = {
        "generated_at": "2025-10-21T10:00:00Z",
        "spots": [
            {
                "spot": "TestSpot",
                "rows": [
                    {
                        "time": "2025-10-21T10:00:00Z",
                        "wind_kn": 25.0,
                        "gust_kn": 30.0,
                        "dir_deg": 0,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": 1.5,
                        "precip_mm_h": 0.0,
                    }
                ],
            }
        ],
        "config": {
            "spots": [
                {
                    "name": "TestSpot",
                    "lat": 43.5,
                    "lon": 3.9,
                    "dir_sector": {"start": 90, "end": 180},
                }
            ],
            "forecast": {
                "model": "test",
                "hourly_vars": "test",
                "wave_vars": "test",
                "forecast_hours_hourly": 48,
                "forecast_min15": 24,
            },
            "time_window": {"day_start": 6, "day_end": 20},
            "conditions": {
                "bands": [["too much", 40], ["hardcore", 35], ["good", 20], ["light", 12]],
                "rain_limit": 2.0,
            },
        },
    }

    # Render report
    output_path = Path("test_report.html")
    renderer.render_html(data, output_path)

    # Parse HTML and check for controls
    with open(output_path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Check for controls div
    controls = soup.find("div", class_="controls")
    assert controls is not None

    # Check for toggle button
    toggle_btn = controls.find("button", id="toggleView")
    assert toggle_btn is not None
    assert toggle_btn.text == "Show All Conditions"

    # Check for search box
    search_box = controls.find("input", id="spotSearch")
    assert search_box is not None
    assert search_box.get("placeholder") == "Search spots..."

    # Clean up
    output_path.unlink()


def test_wind_band_classes():
    """Test that cells have appropriate wind band classes."""
    renderer = ReportRenderer()

    # Create test data with different wind conditions
    data = {
        "generated_at": "2025-10-21T10:00:00Z",
        "spots": [
            {
                "spot": "TestSpot",
                "rows": [
                    {
                        "time": "2025-10-21T10:00:00Z",
                        "wind_kn": 45.0,  # Too much wind
                        "gust_kn": 50.0,
                        "dir_deg": 0,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": 1.5,
                        "precip_mm_h": 0.0,
                    },
                    {
                        "time": "2025-10-21T11:00:00Z",
                        "wind_kn": 37.0,  # Hardcore conditions
                        "gust_kn": 42.0,
                        "dir_deg": 0,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": 1.5,
                        "precip_mm_h": 0.0,
                    },
                    {
                        "time": "2025-10-21T12:00:00Z",
                        "wind_kn": 22.0,  # Good conditions
                        "gust_kn": 27.0,
                        "dir_deg": 0,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": 1.5,
                        "precip_mm_h": 0.0,
                    },
                    {
                        "time": "2025-10-21T13:00:00Z",
                        "wind_kn": 8.0,  # Below kiteable
                        "gust_kn": 12.0,
                        "dir_deg": 0,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": 0.5,
                        "precip_mm_h": 0.0,
                    },
                ],
            }
        ],
        "config": {
            "spots": [
                {
                    "name": "TestSpot",
                    "lat": 43.5,
                    "lon": 3.9,
                    "dir_sector": {"start": 90, "end": 180},
                }
            ],
            "forecast": {
                "model": "test",
                "hourly_vars": "test",
                "wave_vars": "test",
                "forecast_hours_hourly": 48,
                "forecast_min15": 24,
            },
            "time_window": {"day_start": 6, "day_end": 20},
            "conditions": {
                "bands": [["too much", 40], ["hardcore", 35], ["good", 20], ["light", 12]],
                "rain_limit": 2.0,
            },
        },
    }

    # Render report
    output_path = Path("test_report.html")
    renderer.render_html(data, output_path)

    # Parse HTML and check cell classes
    with open(output_path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

        cells = soup.find_all("td")
        cells = [c for c in cells if c.has_attr("class")]  # Keep all cells with classes

        # Check wind band classes
        classes = [c.get("class", []) for c in cells]
        print(
            "Found classes:", classes
        )  # Debug print    assert any('too-much' in c for c in classes), "Missing too-much class"
    assert any("hardcore" in c for c in classes), "Missing hardcore class"
    assert any("good" in c for c in classes), "Missing good class"
    assert any("below" in c for c in classes), "Missing below class"

    # Check kiteable status classes
    assert any("kiteable" in c for c in classes), "Missing kiteable class"
    assert any("not-kiteable" in c for c in classes), "Missing not-kiteable class"

    # Clean up
    output_path.unlink()


def test_initial_cell_visibility():
    """Test that non-kiteable cells and irrelevant columns are initially hidden."""
    renderer = ReportRenderer()

    # Create test data with both kiteable and non-kiteable conditions across multiple spots
    data = {
        "generated_at": "2025-10-21T10:00:00Z",
        "spots": [
            {
                "spot": "TestSpot1",
                "rows": [
                    {
                        "time": "2025-10-21T10:00:00Z",
                        "wind_kn": 25.0,
                        "gust_kn": 30.0,
                        "dir": "N",
                        "kiteable": True,  # This hour should be visible
                        "wave_m": 1.5,
                        "precip_mm_h": 0.0,
                    },
                    {
                        "time": "2025-10-21T11:00:00Z",
                        "wind_kn": 8.0,
                        "gust_kn": 12.0,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": 0.5,
                        "precip_mm_h": 0.0,
                    },
                    {
                        "time": "2025-10-21T12:00:00Z",  # No spots kiteable at this hour
                        "wind_kn": 5.0,
                        "gust_kn": 8.0,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": 0.5,
                        "precip_mm_h": 0.0,
                    },
                ],
            },
            {
                "spot": "TestSpot2",
                "rows": [
                    {
                        "time": "2025-10-21T10:00:00Z",
                        "wind_kn": 15.0,
                        "gust_kn": 20.0,
                        "dir_deg": 0,
                        "dir": "N",
                        "kiteable": True,  # This hour should be visible
                        "wave_m": 1.0,
                        "precip_mm_h": 0.0,
                    },
                    {
                        "time": "2025-10-21T11:00:00Z",
                        "wind_kn": 20.0,
                        "gust_kn": 25.0,
                        "dir_deg": 0,
                        "dir": "N",
                        "kiteable": True,  # This hour should be visible
                        "wave_m": 1.0,
                        "precip_mm_h": 0.0,
                    },
                    {
                        "time": "2025-10-21T12:00:00Z",  # No spots kiteable at this hour
                        "wind_kn": 6.0,
                        "gust_kn": 9.0,
                        "dir_deg": 0,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": 0.5,
                        "precip_mm_h": 0.0,
                    },
                ],
            },
        ],
        "config": {
            "spots": [
                {
                    "name": "TestSpot",
                    "lat": 43.5,
                    "lon": 3.9,
                    "dir_sector": {"start": 90, "end": 180},
                }
            ],
            "forecast": {
                "model": "test",
                "hourly_vars": "test",
                "wave_vars": "test",
                "forecast_hours_hourly": 48,
                "forecast_min15": 24,
            },
            "time_window": {"day_start": 6, "day_end": 20},
            "conditions": {
                "bands": [["too much", 40], ["hardcore", 35], ["good", 20], ["light", 12]],
                "rain_limit": 2.0,
            },
        },
    }

    # Render report
    output_path = Path("test_report.html")
    renderer.render_html(data, output_path)

    # Parse HTML and check initial cell visibility
    with open(output_path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Check cell visibility in kiteable view
    kiteable_view = soup.find("div", id="kiteable-view")
    kiteable_cells = kiteable_view.find_all("td", class_="cell-data")
    for cell in kiteable_cells:
        is_kiteable = "kiteable" in cell.get("class", [])
        display_style = cell.get("style", "")
        if not is_kiteable:
            assert "display:none" in display_style.replace(
                " ", ""
            ) or "style.display='none'" in display_style.replace(
                " ", ""
            ), f"Non-kiteable cell should be hidden in kiteable view: {cell}"

    # Check cell visibility in all-conditions view
    all_view = soup.find("div", id="all-conditions-view")
    all_cells = all_view.find_all("td", class_="cell-data")
    for cell in all_cells:
        display_style = cell.get("style", "")
        # No cells should be hidden in all-conditions view
        assert "display:none" not in display_style.replace(
            " ", ""
        ) and "style.display='none'" not in display_style.replace(
            " ", ""
        ), f"Cells should not be hidden in all-conditions view: {cell}"

    # Check column (hour) visibility
    headers = soup.find_all("th", class_="hour-header")
    for header in headers:
        hour = header.get("data-hour")
        if hour and hour.endswith("T12:00:00"):  # Check the hour where no spots are kiteable
            assert "display:none" in header.get("style", "").replace(
                " ", ""
            ) or "no-kiteable" in header.get(
                "class", []
            ), f"Column for non-kiteable hour should be hidden: {hour}"

        # Verify 10:00 and 11:00 columns are visible (they have kiteable conditions)
        if hour and (hour.endswith("T10:00:00") or hour.endswith("T11:00:00")):
            assert not (
                "display:none" in header.get("style", "").replace(" ", "")
            ), f"Column with kiteable conditions should be visible: {hour}"

    # Clean up
    output_path.unlink()
