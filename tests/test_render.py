"""Test report rendering functionality."""

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from windforecast.render import ReportRenderer


def test_renderer_init():
    """Test ReportRenderer initialization."""
    renderer = ReportRenderer()
    assert renderer.template_dir.is_dir()

    # Test with custom template dir
    custom_dir = Path("/custom/templates")
    renderer = ReportRenderer(template_dir=custom_dir)
    assert renderer.template_dir == custom_dir


def test_calculate_stars():
    """Test star rating calculation based on wind speed."""
    from windforecast.schemas import WindConfig

    # Create a test config
    test_config = WindConfig.model_validate(
        {
            "spots": [
                {
                    "name": "Test Spot",
                    "lat": 0.0,
                    "lon": 0.0,
                    "dir_sector": {"start": 0, "end": 360, "wrap": False},
                }
            ],
            "forecast": {
                "model": "test",
                "hourly_vars": "wind_speed_10m",
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
    )

    renderer = ReportRenderer()
    # Test all bands with expected star ratings
    assert renderer._calculate_stars(42, test_config) == 0  # too much
    assert renderer._calculate_stars(36, test_config) == 3  # hardcore
    assert renderer._calculate_stars(32, test_config) == 6  # insane
    assert renderer._calculate_stars(27, test_config) == 5  # great
    assert renderer._calculate_stars(22, test_config) == 4  # very good
    assert renderer._calculate_stars(18, test_config) == 3  # good
    assert renderer._calculate_stars(16, test_config) == 2  # ok
    assert renderer._calculate_stars(13, test_config) == 1  # light
    assert renderer._calculate_stars(10, test_config) == 0  # below


def test_stars_html():
    """Test HTML star rating generation."""
    renderer = ReportRenderer()
    assert renderer._stars_html(3) == "★★★"
    assert renderer._stars_html(0) == ""


def test_render_html(output_dir):
    """Test HTML report generation."""
    from windforecast.schemas import WindConfig

    # Create test config
    test_config = WindConfig.model_validate(
        {
            "spots": [
                {
                    "name": "Test Spot",
                    "lat": 0.0,
                    "lon": 0.0,
                    "dir_sector": {"start": 0, "end": 360, "wrap": False},
                }
            ],
            "forecast": {
                "model": "test",
                "hourly_vars": "wind_speed_10m",
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
    )

    renderer = ReportRenderer()
    test_data = {
        "generated_at": "2024-03-14T12:00:00Z",
        "model_updates": {"arome_france_hd": {"title": "AROME HD", "run": "2024-03-14T12:00:00Z"}},
        "config": test_config,  # Add the config to the test data
        "spots": [
            {
                "spot": "Test Spot",
                "rows": [
                    {
                        "time": "2024-03-14T12:00:00Z",
                        "wind_kn": 15.5,
                        "gust_kn": 20.1,
                        "dir_deg": 240.0,
                        "dir": "WSW",
                        "precip_mm_h": 0.0,
                        "wave_m": 1.2,
                        "band": "good",
                        "kiteable": True,
                    }
                ],
            }
        ],
    }

    output_path = output_dir / "test_report.html"
    renderer.render_html(test_data, output_path)

    assert output_path.exists()
    content = output_path.read_text()
    # Basic content checks
    assert "Test Spot" in content
    assert "WSW" in content
    assert "15.5" in content
    assert "★★" in content  # Should show 2 stars for 15.5 knots
    assert "🌊 1.2m" in content


def test_render_html_no_kiteable(output_dir):
    """Test HTML rendering with no kiteable conditions."""
    from windforecast.schemas import WindConfig

    # Create test config
    test_config = WindConfig.model_validate(
        {
            "spots": [
                {
                    "name": "Test Spot",
                    "lat": 0.0,
                    "lon": 0.0,
                    "dir_sector": {"start": 0, "end": 360, "wrap": False},
                }
            ],
            "forecast": {
                "model": "test",
                "hourly_vars": "wind_speed_10m",
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
    )

    renderer = ReportRenderer()
    test_data = {
        "generated_at": "2024-03-14T12:00:00Z",
        "model_updates": {},
        "config": test_config,  # Add the config to the test data
        "spots": [
            {
                "spot": "Test Spot",
                "rows": [
                    {
                        "time": "2024-03-14T12:00:00Z",
                        "wind_kn": 8.0,
                        "gust_kn": 10.0,
                        "dir_deg": 240.0,
                        "dir": "WSW",
                        "precip_mm_h": 0.0,
                        "wave_m": None,
                        "band": "light",
                        "kiteable": False,
                    }
                ],
            }
        ],
    }

    output_path = output_dir / "test_report.html"
    renderer.render_html(test_data, output_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "No kiteable conditions found" in content
