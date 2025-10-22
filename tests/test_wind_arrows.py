"""Test wind direction arrows in HTML report."""

import json
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from windforecast.render import ReportRenderer
from windforecast.schemas import WindConfig


def test_wind_direction_arrows():
    """Test that wind direction arrows point where the wind is blowing (180° from source direction)."""
    # Sample data with various wind directions
    config = {
        "spots": [
            {
                "name": "Test Spot",
                "lat": 41.3948,
                "lon": 2.2105,
                "dir_sector": {"start": 0, "end": 360, "wrap": False},
            }
        ],
        "forecast": {
            "model": "arome_france_hd",
            "hourly_vars": "wind_speed_10m,wind_gusts_10m,wind_direction_10m,precipitation",
            "wave_vars": "wave_height",
            "forecast_hours_hourly": 48,
            "forecast_min15": 24,
        },
        "time_window": {"day_start": 6, "day_end": 20},
        "conditions": {
            "bands": [
                ["too much", 40],
                ["hardcore", 35],
                ["insane", 30],
                ["great", 25],
                ["very good", 20],
                ["good", 17],
                ["ok", 15],
                ["light", 12],
                ["below", 0],
            ],
            "rain_limit": 0.5,
        },
    }

    test_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "spots": [
            {
                "spot": "Test Spot",
                "rows": [
                    {
                        "time": "2025-10-23T12:00:00Z",
                        "wind_kn": 15.0,
                        "gust_kn": 20.0,
                        "dir_deg": 0,  # Wind from North (should point South)
                        "dir": "N",
                        "precip_mm_h": 0.0,
                        "wave_m": None,
                        "kiteable": True,
                    },
                    {
                        "time": "2025-10-23T13:00:00Z",
                        "wind_kn": 15.0,
                        "gust_kn": 20.0,
                        "dir_deg": 90,  # Wind from East (should point West)
                        "dir": "E",
                        "precip_mm_h": 0.0,
                        "wave_m": None,
                        "kiteable": True,
                    },
                    {
                        "time": "2025-10-23T14:00:00Z",
                        "wind_kn": 15.0,
                        "gust_kn": 20.0,
                        "dir_deg": 180,  # Wind from South (should point North)
                        "dir": "S",
                        "precip_mm_h": 0.0,
                        "wave_m": None,
                        "kiteable": True,
                    },
                    {
                        "time": "2025-10-23T15:00:00Z",
                        "wind_kn": 15.0,
                        "gust_kn": 20.0,
                        "dir_deg": 270,  # Wind from West (should point East)
                        "dir": "W",
                        "precip_mm_h": 0.0,
                        "wave_m": None,
                        "kiteable": True,
                    },
                ],
            }
        ],
        "config": config,
    }

    # Create renderer and generate HTML
    renderer = ReportRenderer(config=WindConfig.model_validate(config))
    output_path = Path("test_report.html")
    renderer.render_html(test_data, output_path)

    # Parse HTML and check arrow rotations
    with open(output_path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Get wind direction arrows from the kiteable view only
    kiteable_view = soup.find(id="kiteable-view")
    arrows = kiteable_view.find_all("span", class_="dir-arrow")
    expected_rotations = [
        180,  # N → S (0° + 180°)
        270,  # E → W (90° + 180°)
        360,  # S → N (180° + 180° = 360°)
        450,  # W → E (270° + 180° = 450°)
    ]

    assert len(arrows) == len(expected_rotations), "Wrong number of wind direction arrows"

    for arrow, expected_deg in zip(arrows, expected_rotations):
        style = arrow.get("style", "")
        assert (
            f"transform: rotate({expected_deg}deg)" in style
        ), f"Arrow should point to {expected_deg}° but style was {style}"

    # Clean up
    output_path.unlink()
