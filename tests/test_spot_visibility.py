"""Tests for spot visibility in different views."""

import datetime
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from windforecast.render import ReportRenderer
from windforecast.schemas import WindConfig


def test_spot_visibility_in_kiteable_view():
    """Test that spots with no kiteable conditions are not shown in kiteable view."""
    # Create test data
    test_data = {
        "generated_at": "2025-10-22T10:00:00Z",
        "config": {
            "spots": [
                {
                    "name": "Test Beach",
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
                "bands": [
                    ["too much", 35],
                    ["hardcore", 30],
                    ["insane", 25],
                    ["great", 20],
                    ["very good", 18],
                    ["good", 15],
                    ["ok", 12],
                    ["light", 8],
                    ["below", 0],
                ],
                "min_kiteable": 12,  # "ok" and above are kiteable
                "max_kiteable": 35,
                "rain_limit": 0.5,
            },
        },
        "spots": [
            {
                "spot": "Kiteable Beach",  # This spot will have kiteable conditions
                "rows": [
                    {
                        "time": "2025-10-22T12:00:00Z",
                        "wind_kn": 15,
                        "gust_kn": 18,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": None,
                        "precip_mm_h": 0,
                    }
                ],
            },
            {
                "spot": "Never Kiteable Beach",  # This spot will have no kiteable conditions
                "rows": [
                    {
                        "time": "2025-10-22T12:00:00Z",
                        "wind_kn": 10,
                        "gust_kn": 11,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": None,
                        "precip_mm_h": 0,
                    }
                ],
            },
        ],
    }

    # Create temporary output file
    output_path = Path("test_output.html")

    # Render the report
    renderer = ReportRenderer()
    renderer.render_html(test_data, output_path)

    # Parse the generated HTML
    with open(output_path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Test kiteable view
    kiteable_view = soup.find("div", id="kiteable-view")
    kiteable_spot_cells = kiteable_view.find_all("td", class_="spotcol")
    kiteable_spot_names = [cell.find("strong").text for cell in kiteable_spot_cells]

    # Check that only kiteable spots are shown
    assert "Kiteable Beach" in kiteable_spot_names, "Kiteable spot should be shown"
    assert (
        "Never Kiteable Beach" not in kiteable_spot_names
    ), "Non-kiteable spot should not be shown"

    # Test all-conditions view
    all_view = soup.find("div", id="all-conditions-view")
    all_spot_cells = all_view.find_all("td", class_="spotcol")
    all_spot_names = [cell.find("strong").text for cell in all_spot_cells]

    # Check that all spots are shown in all-conditions view
    assert "Kiteable Beach" in all_spot_names, "Kiteable spot should be shown in all view"
    assert "Never Kiteable Beach" in all_spot_names, "Non-kiteable spot should be shown in all view"

    # Cleanup
    output_path.unlink()
