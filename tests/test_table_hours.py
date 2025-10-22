"""Tests for table hour filtering in ReportRenderer."""

import datetime
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from windforecast.render import ReportRenderer
from windforecast.schemas import WindConfig


def test_table_hours():
    """Test that tables contain correct hours based on view."""
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
                "spot": "Test Beach",
                "rows": [
                    # Not kiteable hours
                    {
                        "time": "2025-10-22T06:00:00Z",
                        "wind_kn": 10,  # Below min_kiteable
                        "gust_kn": 12,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": None,
                        "precip_mm_h": 0,
                    },
                    {
                        "time": "2025-10-22T07:00:00Z",
                        "wind_kn": 11,  # Below min_kiteable
                        "gust_kn": 13,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": None,
                        "precip_mm_h": 0,
                    },
                    # Kiteable hours
                    {
                        "time": "2025-10-22T12:00:00Z",
                        "wind_kn": 15,
                        "gust_kn": 18,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": None,
                        "precip_mm_h": 0,
                    },
                    {
                        "time": "2025-10-22T13:00:00Z",
                        "wind_kn": 20,
                        "gust_kn": 25,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": None,
                        "precip_mm_h": 0,
                    },
                    # Not kiteable hours
                    {
                        "time": "2025-10-22T19:00:00Z",
                        "wind_kn": 10,  # Below min_kiteable
                        "gust_kn": 12,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": None,
                        "precip_mm_h": 0,
                    },
                    {
                        "time": "2025-10-22T20:00:00Z",
                        "wind_kn": 9,  # Below min_kiteable
                        "gust_kn": 11,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": None,
                        "precip_mm_h": 0,
                    },
                ],
            }
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

    # Test all-conditions view
    all_view = soup.find("div", id="all-conditions-view")
    all_hours = [th.text.strip() for th in all_view.find_all("th") if th.text.strip() != "Spot"]

    # Check that all hours between 6:00 and 20:00 are present in all-conditions view
    expected_hours = ["06:00", "07:00", "12:00", "13:00", "19:00", "20:00"]
    assert (
        all_hours == expected_hours
    ), f"Expected {expected_hours}, got {all_hours} in all-conditions view"

    # Test kiteable view
    kiteable_view = soup.find("div", id="kiteable-view")
    kiteable_hours = [
        th.text.strip() for th in kiteable_view.find_all("th") if th.text.strip() != "Spot"
    ]

    # Check that only hours with kiteable conditions are present in kiteable view
    expected_kiteable_hours = ["12:00", "13:00"]
    assert (
        kiteable_hours == expected_kiteable_hours
    ), f"Expected {expected_kiteable_hours}, got {kiteable_hours} in kiteable view"

    # Cleanup
    output_path.unlink()
