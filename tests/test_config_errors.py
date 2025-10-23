"""Tests for configuration error handling."""

import json
from pathlib import Path

import pytest

from windforecast.config import load_config


def create_base_config():
    """Create a valid base config for tests to modify."""
    return {
        "spots": [
            {"name": "Test Spot", "lat": 45.0, "lon": -1.0, "dir_sector": {"start": 90, "end": 270}}
        ],
        "forecast": {
            "model": "arome_france_hd",
            "hourly_vars": "wind_speed_10m,wind_direction_10m",
            "wave_vars": "wave_height",
            "forecast_hours_hourly": 48,
            "forecast_min15": 24,
        },
        "time_window": {"day_start": 8, "day_end": 20},
        "conditions": {"bands": [["too much", 40], ["good", 20], ["light", 12]], "rain_limit": 0.5},
    }


def write_config(tmp_path, config_data):
    """Helper to write config to file."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))
    return config_file


def test_config_json_decode_error(tmp_path):
    """Test handling of invalid JSON in config file."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{invalid json")

    with pytest.raises(ValueError, match="Invalid JSON in config file"):
        load_config(config_file)


def test_config_invalid_thresholds(tmp_path):
    """Test validation of wind band thresholds."""
    config_data = create_base_config()
    config_data["conditions"]["bands"] = [
        ["too much", 40],
        ["hardcore", 35],
        ["good", 20],
        ["light", 25],  # Invalid: not strictly descending
    ]

    with pytest.raises(ValueError, match="Band thresholds must be in strictly descending order"):
        load_config(write_config(tmp_path, config_data))


def test_config_invalid_day_times(tmp_path):
    """Test validation of day start/end times."""
    config_data = create_base_config()
    config_data["time_window"] = {"day_start": 20, "day_end": 8}  # Invalid: start after end

    with pytest.raises(ValueError, match="day_end must be after day_start"):
        load_config(write_config(tmp_path, config_data))
