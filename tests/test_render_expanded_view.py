"""Tests for expanded view and search functionality in HTML reports."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from windforecast.render import ReportRenderer


def create_test_data(spot_name="TestSpot", wind_kn=25.0, kiteable=True):
    """Helper to create minimal test data with sensible defaults."""
    return {
        "generated_at": "2025-10-21T10:00:00Z",
        "spots": [
            {
                "spot": spot_name,
                "rows": [
                    {
                        "time": "2025-10-21T10:00:00Z",
                        "wind_kn": wind_kn,
                        "gust_kn": wind_kn + 5,
                        "dir": "N",
                        "kiteable": kiteable,
                        "wave_m": 1.5,
                        "precip_mm_h": 0.0,
                    }
                ],
            }
        ],
        "config": {
            "spots": [
                {
                    "name": spot_name,
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


def render_and_parse(data, output_path):
    """Helper to render HTML and return parsed BeautifulSoup object."""
    renderer = ReportRenderer()
    renderer.render_html(data, output_path)
    with open(output_path) as f:
        return BeautifulSoup(f.read(), "html.parser")


def test_expanded_view_controls(tmp_path):
    """Test that expanded view controls are present in the HTML."""
    output_path = tmp_path / "test_report.html"
    soup = render_and_parse(create_test_data(), output_path)

    # Check for controls with concise assertions
    controls = soup.find("div", class_="controls")
    assert controls, "Controls div should exist"

    toggle_btn = controls.find("button", id="toggleView")
    assert (
        toggle_btn and toggle_btn.text == "Show All Conditions"
    ), "Toggle button should exist with correct text"

    search_box = controls.find("input", id="spotSearch")
    assert (
        search_box and search_box.get("placeholder") == "Search spots..."
    ), "Search box should exist with placeholder"


def test_wind_band_classes(tmp_path):
    """Test that cells have appropriate wind band classes."""
    # Create test data with multiple wind conditions in a single spot
    data = create_test_data()
    data["spots"][0]["rows"] = [
        {
            "time": "2025-10-21T10:00:00Z",
            "wind_kn": 45.0,
            "gust_kn": 50.0,
            "dir": "N",
            "kiteable": False,
            "wave_m": 1.5,
            "precip_mm_h": 0.0,
        },
        {
            "time": "2025-10-21T11:00:00Z",
            "wind_kn": 37.0,
            "gust_kn": 42.0,
            "dir": "N",
            "kiteable": True,
            "wave_m": 1.5,
            "precip_mm_h": 0.0,
        },
        {
            "time": "2025-10-21T12:00:00Z",
            "wind_kn": 22.0,
            "gust_kn": 27.0,
            "dir": "N",
            "kiteable": True,
            "wave_m": 1.5,
            "precip_mm_h": 0.0,
        },
        {
            "time": "2025-10-21T13:00:00Z",
            "wind_kn": 8.0,
            "gust_kn": 12.0,
            "dir": "N",
            "kiteable": False,
            "wave_m": 0.5,
            "precip_mm_h": 0.0,
        },
    ]

    output_path = tmp_path / "test_report.html"
    soup = render_and_parse(data, output_path)

    # Get all cell classes
    all_classes = [" ".join(c.get("class", [])) for c in soup.find_all("td") if c.has_attr("class")]

    # Check expected classes are present
    assert any("too-much" in c for c in all_classes), "Missing too-much class"
    assert any("hardcore" in c for c in all_classes), "Missing hardcore class"
    assert any("good" in c for c in all_classes), "Missing good class"
    assert any("below" in c for c in all_classes), "Missing below class"
    assert any("kiteable" in c for c in all_classes), "Missing kiteable class"
    assert any("not-kiteable" in c for c in all_classes), "Missing not-kiteable class"


def test_initial_cell_visibility(tmp_path):
    """Test that non-kiteable cells are hidden in kiteable view but visible in all-conditions view."""
    # Create multi-spot data with mixed kiteable/non-kiteable conditions
    data = create_test_data("TestSpot1")
    data["spots"].extend([create_test_data("TestSpot2", wind_kn=15.0)["spots"][0]])

    # Add times: 10:00 (both kiteable), 11:00 (one kiteable), 12:00 (none kiteable)
    for i, spot_data in enumerate(data["spots"]):
        spot_data["rows"] = [
            {
                "time": "2025-10-21T10:00:00Z",
                "wind_kn": 25.0 if i == 0 else 15.0,
                "gust_kn": 30.0 if i == 0 else 20.0,
                "dir": "N",
                "kiteable": True,
                "wave_m": 1.0,
                "precip_mm_h": 0.0,
            },
            {
                "time": "2025-10-21T11:00:00Z",
                "wind_kn": 8.0 if i == 0 else 20.0,
                "gust_kn": 12.0 if i == 0 else 25.0,
                "dir": "N",
                "kiteable": False if i == 0 else True,
                "wave_m": 0.5,
                "precip_mm_h": 0.0,
            },
            {
                "time": "2025-10-21T12:00:00Z",
                "wind_kn": 5.0,
                "gust_kn": 8.0,
                "dir": "N",
                "kiteable": False,
                "wave_m": 0.5,
                "precip_mm_h": 0.0,
            },
        ]

    output_path = tmp_path / "test_report.html"
    soup = render_and_parse(data, output_path)

    # In kiteable view: non-kiteable cells should be hidden
    kiteable_view = soup.find("div", id="kiteable-view")
    kiteable_cells = kiteable_view.find_all("td", class_="cell-data")
    non_kiteable_cells = [c for c in kiteable_cells if "not-kiteable" in c.get("class", [])]
    assert all(
        "display:none" in c.get("style", "").replace(" ", "") for c in non_kiteable_cells
    ), "Non-kiteable cells should be hidden in kiteable view"

    # In all-conditions view: all cells should be visible
    all_view = soup.find("div", id="all-conditions-view")
    all_cells = all_view.find_all("td", class_="cell-data")
    assert all(
        "display:none" not in c.get("style", "").replace(" ", "") for c in all_cells
    ), "All cells should be visible in all-conditions view"
