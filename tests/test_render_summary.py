"""Tests for daily summary generation."""

from pathlib import Path

from windforecast.render import ReportRenderer
from windforecast.schemas import WindConfig


def create_test_config(spots):
    """Create a test config with provided spots."""
    return {
        "spots": [
            {"name": spot, "lat": 43.5, "lon": 3.9, "dir_sector": {"start": 90, "end": 180}}
            for spot in spots
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
            "bands": [["too much", 40], ["hardcore", 35], ["good", 20], ["light", 12]],
            "rain_limit": 2.0,
        },
    }


def test_daily_summary_generation():
    """Test generation of daily summary with kiteable conditions."""
    renderer = ReportRenderer()
    data = {
        "spots": [
            {
                "spot": "Spot1",
                "rows": [
                    {
                        "time": "2025-10-19T09:00:00Z",
                        "wind_kn": 25.0,
                        "gust_kn": 30.0,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": 1.5,
                        "precip_mm_h": 0.0,
                    },
                    {
                        "time": "2025-10-19T10:00:00Z",
                        "wind_kn": 28.0,
                        "gust_kn": 32.0,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": 1.8,
                        "precip_mm_h": 0.0,
                    },
                ],
            },
            {
                "spot": "Spot2",
                "rows": [
                    {
                        "time": "2025-10-19T09:00:00Z",
                        "wind_kn": 22.0,
                        "gust_kn": 26.0,
                        "dir": "NE",
                        "kiteable": True,
                        "wave_m": 1.2,
                        "precip_mm_h": 0.0,
                    }
                ],
            },
        ],
        "config": {
            "spots": [
                {"name": "Spot1", "lat": 43.5, "lon": 3.9, "dir_sector": {"start": 90, "end": 180}},
                {"name": "Spot2", "lat": 43.6, "lon": 3.8, "dir_sector": {"start": 90, "end": 180}},
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
                "bands": [["too much", 40], ["hardcore", 35], ["good", 20], ["light", 12]],
                "rain_limit": 2.0,
            },
        },
    }

    # Create all_forecasts dictionary
    all_forecasts = {}
    spots = []
    for spot in data["spots"]:
        spots.append(spot["spot"])
        for r in spot["rows"]:
            time = r["time"]
            if time not in all_forecasts:
                all_forecasts[time] = {}
            all_forecasts[time][spot["spot"]] = r

    # Generate summary
    summary = renderer._generate_daily_summary(data, spots, all_forecasts)

    # Verify summary shows kiteable conditions
    assert summary is not None
    assert "Spot1" in summary
    assert "Spot2" in summary
    assert "2 kiteable hours" in summary  # Spot1 has 2 kiteable hours
    assert "1 kiteable hours" in summary  # Spot2 has 1 kiteable hour
    assert "09:00-10:00" in summary  # Time range for Spot1
    assert "09:00" in summary  # Single time for Spot2
    assert "Avg wind" in summary
    assert "Max gust" in summary


def test_daily_summary_no_kiteable():
    """Test daily summary generation with no kiteable conditions."""
    renderer = ReportRenderer()

    # Test with non-kiteable conditions
    data = {
        "spots": [
            {
                "spot": "Spot1",
                "rows": [
                    {
                        "time": "2025-10-19T09:00:00Z",
                        "wind_kn": 5.0,
                        "gust_kn": 8.0,
                        "dir": "N",
                        "kiteable": False,
                        "wave_m": 0.5,
                        "precip_mm_h": 0.0,
                    }
                ],
            }
        ],
        "config": create_test_config(["Spot1", "Spot2"]),
        "generated_at": "2025-10-19T09:00:00Z",
    }  # Create all_forecasts dictionary
    all_forecasts = {}
    spots = []
    for spot in data["spots"]:
        spots.append(spot["spot"])
        for r in spot["rows"]:
            time = r["time"]
            if time not in all_forecasts:
                all_forecasts[time] = {}
            all_forecasts[time][spot["spot"]] = r

    # Generate summary
    summary = renderer._generate_daily_summary(data, spots, all_forecasts)
    # Verify an empty summary grid is returned
    assert summary is not None
    assert '<div class="daily-grid"></div>' in summary
    assert "kiteable hour" not in summary
    assert "daily-summary" in summary

    # Test with empty rows
    data = {"spots": [{"spot": "Spot1", "rows": []}], "config": create_test_config(["Spot1"])}

    # Create all_forecasts dictionary for empty case
    all_forecasts = {}
    spots = [spot["spot"] for spot in data["spots"]]

    # Generate summary
    summary = renderer._generate_daily_summary(data, spots, all_forecasts)
    # Verify no summary is generated
    assert summary is None

    # Test with no spots
    data = {"spots": [], "config": create_test_config(["Spot1"])}  # Config still needs a spot

    # Create all_forecasts dictionary for no spots case
    all_forecasts = {}
    spots = []

    # Generate summary
    summary = renderer._generate_daily_summary(data, spots, all_forecasts)
    # Verify no summary is generated
    assert summary is None


def test_daily_summary_multiple_days():
    """Test daily summary generation with data spanning multiple days."""
    renderer = ReportRenderer()
    data = {
        "spots": [
            {
                "spot": "Spot1",
                "rows": [
                    {
                        "time": "2025-10-19T09:00:00Z",
                        "wind_kn": 25.0,
                        "gust_kn": 30.0,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": 1.5,
                        "precip_mm_h": 0.0,
                    },
                    {
                        "time": "2025-10-20T09:00:00Z",
                        "wind_kn": 28.0,
                        "gust_kn": 32.0,
                        "dir": "N",
                        "kiteable": True,
                        "wave_m": 1.8,
                        "precip_mm_h": 0.0,
                    },
                ],
            }
        ],
        "config": create_test_config(["Spot1"]),
    }

    # Create all_forecasts dictionary
    all_forecasts = {}
    spots = []
    for spot in data["spots"]:
        spots.append(spot["spot"])
        for r in spot["rows"]:
            time = r["time"]
            if time not in all_forecasts:
                all_forecasts[time] = {}
            all_forecasts[time][spot["spot"]] = r

    # Generate summary
    summary = renderer._generate_daily_summary(data, spots, all_forecasts)

    # Verify summary content
    assert summary is not None
    assert "1 kiteable hour" in summary  # Each day has 1 kiteable hour
    assert "25.0kt" in summary
    assert "28.0kt" in summary
