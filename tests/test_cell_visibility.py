"""Tests for cell visibility in different views."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from windforecast.render import ReportRenderer


def create_test_data_with_mixed_conditions():
    """Create test data with both kiteable and non-kiteable conditions."""
    return {
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
                    ["good", 15],
                    ["light", 8],
                    ["below", 0],
                ],
                "rain_limit": 0.5,
            },
        },
        "spots": [
            {
                "spot": "Test Beach",
                "rows": [
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
                        "wind_kn": 10,
                        "gust_kn": 12,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": None,
                        "precip_mm_h": 0,
                    },
                ],
            }
        ],
    }


def test_all_conditions_visibility(tmp_path):
    """Test that all cells are visible in the all-conditions view."""
    output_path = tmp_path / "test_output.html"
    renderer = ReportRenderer()
    renderer.render_html(create_test_data_with_mixed_conditions(), output_path)

    soup = BeautifulSoup(output_path.read_text(), "html.parser")
    all_view = soup.find("div", id="all-conditions-view")
    all_cells = all_view.find_all("td", class_="cell-data")

    # Verify we have cells and none are hidden
    assert len(all_cells) > 0, "No data cells found in all-conditions view"
    hidden_cells = [c for c in all_cells if "display: none" in c.get("style", "")]
    assert len(hidden_cells) == 0, f"Found {len(hidden_cells)} hidden cells in all-conditions view"

    # Verify both kiteable and non-kiteable cells exist
    kiteable_cells = [c for c in all_cells if "kiteable" in c.get("class", [])]
    not_kiteable_cells = [c for c in all_cells if "not-kiteable" in c.get("class", [])]
    assert len(kiteable_cells) > 0 and len(not_kiteable_cells) > 0, "Both cell types should exist"
