"""Test fixtures for the windforecast package."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_config_data():
    """Sample configuration data."""
    return {
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
            "hourly_vars": "wind_speed_10m,wind_gusts_10m,wind_direction_10m,precipitation",
            "wave_vars": "wave_height",
            "forecast_hours_hourly": 48,
            "forecast_min15": 24,
        },
        "time_window": {"day_start": 6, "day_end": 20},
        "conditions": {
            "bands": [["too much", 40], ["good", 17], ["light", 12], ["below", 0]],
            "rain_limit": 0.5,
        },
    }


@pytest.fixture
def config_file(tmp_path, sample_config_data):
    """Creates a temporary config.json file."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sample_config_data, f, indent=2)
    return config_path


@pytest.fixture
def sample_forecast_data():
    """Sample forecast API response data."""
    return {
        "hourly": {
            "time": ["2024-03-14T12:00:00Z", "2024-03-14T13:00:00Z"],
            "wind_speed_10m": [15.5, 16.2],
            "wind_gusts_10m": [20.1, 21.3],
            "wind_direction_10m": [240, 245],
            "precipitation": [0.0, 0.2],
        }
    }


@pytest.fixture
def sample_wave_data():
    """Sample wave API response data."""
    return {
        "hourly": {
            "time": ["2024-03-14T12:00:00Z", "2024-03-14T13:00:00Z"],
            "wave_height": [1.2, 1.3],
        }
    }


@pytest.fixture
def output_dir(tmp_path):
    """Creates a temporary output directory."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    return out_dir
