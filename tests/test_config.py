"""Test configuration loading and validation."""

import json
from pathlib import Path

import pytest

from windforecast.config import load_config
from windforecast.schemas import WindConfig


def test_load_config_valid(config_file):
    """Test loading a valid configuration file."""
    config = load_config(config_file)
    assert isinstance(config, WindConfig)
    assert len(config.spots) == 1
    assert config.spots[0].name == "Test Spot"
    assert config.forecast.model == "arome_france_hd"


def test_load_config_missing_file():
    """Test error handling when config file is missing."""
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.json"))


def test_invalid_json(tmp_path):
    """Test error handling for invalid JSON."""
    config_path = tmp_path / "config.json"
    config_path.write_text("{invalid: json}")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_config(config_path)


@pytest.mark.parametrize(
    "field,invalid_value,expected_error",
    [
        ("spots[0].lat", 100, "Input should be less than or equal to 90"),
        ("spots[0].lon", -200, "Input should be greater than or equal to -180"),
        ("spots[0].dir_sector.start", 400, "Input should be less than or equal to 360"),
        ("forecast.forecast_hours_hourly", 0, "Input should be greater than 0"),
        ("conditions.rain_limit", -1, "Input should be greater than or equal to 0"),
    ],
)
def test_invalid_values(config_file, field, invalid_value, expected_error):
    """Test validation of invalid field values."""
    # Load valid config
    with open(config_file) as f:
        data = json.load(f)

    # Modify field
    parts = field.split(".")
    target = data

    for part in parts[:-1]:
        # Handle array indexing
        if "[" in part:
            name, idx = part[:-3], int(part[-2])
            target = target[name][idx]
        else:
            target = target[part]

    key = parts[-1]
    target[key] = invalid_value

    # Write modified config
    invalid_config = config_file.parent / "invalid_config.json"
    with open(invalid_config, "w") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match=expected_error):
        load_config(invalid_config)


def test_invalid_time_window(config_file):
    """Test validation of time window."""
    with open(config_file) as f:
        data = json.load(f)

    # Set end before start
    data["time_window"]["day_start"] = 18
    data["time_window"]["day_end"] = 6

    invalid_config = config_file.parent / "invalid_time.json"
    with open(invalid_config, "w") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="day_end must be after day_start"):
        load_config(invalid_config)


def test_invalid_bands_order(config_file):
    """Test validation of wind speed bands order."""
    with open(config_file) as f:
        data = json.load(f)

    # Set bands in wrong order
    data["conditions"]["bands"] = [["light", 12], ["good", 17], ["too much", 15]]  # Wrong order

    invalid_config = config_file.parent / "invalid_bands.json"
    with open(invalid_config, "w") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Band thresholds must be in strictly descending order"):
        load_config(invalid_config)
