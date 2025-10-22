"""Tests for cell visibility in different views."""

import datetime
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from windforecast.render import ReportRenderer
from windforecast.schemas import WindConfig


def test_all_conditions_visibility():
    """Test that all cells are visible in the all-conditions view."""
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
                    # Mix of kiteable and non-kiteable conditions
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

    # Get all data cells (excluding header and spot column)
    all_cells = all_view.find_all("td", class_="cell-data")

    # Verify that we have some cells to test
    assert len(all_cells) > 0, "No data cells found in all-conditions view"

    # Check that none of the cells in all-conditions view have style="display: none"
    hidden_cells = [
        cell for cell in all_cells if "style" in cell.attrs and "display: none" in cell["style"]
    ]
    assert len(hidden_cells) == 0, f"Found {len(hidden_cells)} hidden cells in all-conditions view"

    # Also verify that both kiteable and not-kiteable cells exist
    kiteable_cells = [cell for cell in all_cells if "kiteable" in cell.get("class", [])]
    not_kiteable_cells = [cell for cell in all_cells if "not-kiteable" in cell.get("class", [])]

    assert len(kiteable_cells) > 0, "No kiteable cells found"
    assert len(not_kiteable_cells) > 0, "No not-kiteable cells found"

    # Cleanup
    output_path.unlink()
