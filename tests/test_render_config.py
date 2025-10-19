"""Tests for configuration and initialization."""

from pathlib import Path

import pytest

from windforecast.render import ReportRenderer
from windforecast.schemas import (
    Conditions,
    DirectionSector,
    ForecastConfig,
    TimeWindow,
    WindConfig,
    WindSpot,
)


def test_renderer_initialization():
    """Test renderer initialization with different parameters."""
    # Test default initialization
    renderer = ReportRenderer()
    assert renderer.config is None
    assert (
        renderer.template_dir == Path(__file__).parent.parent / "src" / "windforecast" / "templates"
    )

    # Test with custom config
    config = WindConfig(
        spots=[
            WindSpot(name="spot1", lat=43.5, lon=3.9, dir_sector=DirectionSector(start=90, end=180))
        ],
        forecast=ForecastConfig(
            model="arome_france_hd",
            hourly_vars="wind_speed_10m,wind_direction_10m",
            wave_vars="wave_height",
            forecast_hours_hourly=48,
            forecast_min15=24,
        ),
        time_window=TimeWindow(day_start=6, day_end=20),
        conditions=Conditions(
            bands=[
                ["too much", 40],
                ["hardcore", 35],
                ["good", 20],
                ["light", 12],
            ],
            rain_limit=2.0,
        ),
    )
    renderer = ReportRenderer(config=config)
    assert renderer.config == config

    # Test with custom template directory
    custom_dir = Path("/custom/templates")
    renderer = ReportRenderer(template_dir=custom_dir)
    assert renderer.template_dir == custom_dir

    # Test with invalid config (no spots)
    with pytest.raises(ValueError, match="List should have at least 1 item"):
        invalid_config = WindConfig(
            spots=[],  # Empty spots list
            forecast=ForecastConfig(
                model="arome_france_hd",
                hourly_vars="wind_speed_10m,wind_direction_10m",
                wave_vars="wave_height",
                forecast_hours_hourly=48,
                forecast_min15=24,
            ),
            time_window=TimeWindow(day_start=6, day_end=20),
            conditions=Conditions(
                bands=[
                    ["too much", 40],
                    ["hardcore", 35],
                    ["good", 20],
                    ["light", 12],
                ],
                rain_limit=2.0,
            ),
        )

    # Test with invalid time window
    with pytest.raises(ValueError, match="Input should be less than or equal to 23"):
        invalid_config = WindConfig(
            spots=[
                WindSpot(
                    name="spot1", lat=43.5, lon=3.9, dir_sector=DirectionSector(start=90, end=180)
                )
            ],
            forecast=ForecastConfig(
                model="arome_france_hd",
                hourly_vars="wind_speed_10m,wind_direction_10m",
                wave_vars="wave_height",
                forecast_hours_hourly=48,
                forecast_min15=24,
            ),
            time_window=TimeWindow(day_start=24, day_end=20),  # Invalid start hour
            conditions=Conditions(
                bands=[
                    ["too much", 40],
                    ["hardcore", 35],
                    ["good", 20],
                    ["light", 12],
                ],
                rain_limit=2.0,
            ),
        )

    # Test with invalid direction sector
    with pytest.raises(ValueError, match="Input should be less than or equal to 360"):
        invalid_config = WindConfig(
            spots=[
                WindSpot(
                    name="spot1",
                    lat=43.5,
                    lon=3.9,
                    dir_sector=DirectionSector(start=400, end=180),  # Invalid start angle
                )
            ],
            forecast=ForecastConfig(
                model="arome_france_hd",
                hourly_vars="wind_speed_10m,wind_direction_10m",
                wave_vars="wave_height",
                forecast_hours_hourly=48,
                forecast_min15=24,
            ),
            time_window=TimeWindow(day_start=6, day_end=20),
            conditions=Conditions(
                bands=[
                    ["too much", 40],
                    ["hardcore", 35],
                    ["good", 20],
                    ["light", 12],
                ],
                rain_limit=2.0,
            ),
        )


def test_star_calculation():
    """Test wind speed to star rating calculation."""
    config = WindConfig(
        spots=[
            WindSpot(name="spot1", lat=43.5, lon=3.9, dir_sector=DirectionSector(start=90, end=180))
        ],
        forecast=ForecastConfig(
            model="arome_france_hd",
            hourly_vars="wind_speed_10m,wind_direction_10m",
            wave_vars="wave_height",
            forecast_hours_hourly=48,
            forecast_min15=24,
        ),
        time_window=TimeWindow(day_start=6, day_end=20),
        conditions=Conditions(
            bands=[
                ["too much", 40],
                ["hardcore", 35],
                ["good", 20],
                ["light", 12],
            ],
            rain_limit=2.0,
        ),
    )
    renderer = ReportRenderer(config=config)

    # Test different wind speeds
    assert renderer._calculate_stars(45, config) == 0  # Too much wind
    assert renderer._calculate_stars(37, config) == 3  # Hardcore conditions
    assert renderer._calculate_stars(25, config) == 3  # Good conditions
    assert renderer._calculate_stars(15, config) == 1  # Light conditions
    assert renderer._calculate_stars(10, config) == 0  # Too light

    # Test edge cases
    assert renderer._calculate_stars(40, config) == 0  # Exactly at "too much" threshold
    assert renderer._calculate_stars(35, config) == 3  # Exactly at "hardcore" threshold
    assert renderer._calculate_stars(20, config) == 3  # Exactly at "good" threshold
    assert renderer._calculate_stars(12, config) == 1  # Exactly at "light" threshold


def test_stars_html_generation():
    """Test HTML star rating generation."""
    renderer = ReportRenderer()
    assert renderer._stars_html(0) == ""  # No stars
    assert renderer._stars_html(1) == "★"  # One star
    assert renderer._stars_html(3) == "★★★"  # Three stars
    assert renderer._stars_html(5) == "★★★★★"  # Five stars
    # Test negative values should return empty string
    assert renderer._stars_html(-1) == ""


def test_invalid_conditions():
    """Test configuration validation with invalid conditions."""
    # Test negative rain limit
    with pytest.raises(ValueError, match="Input should be greater than or equal to 0"):
        invalid_config = WindConfig(
            spots=[
                WindSpot(
                    name="spot1", lat=43.5, lon=3.9, dir_sector=DirectionSector(start=90, end=180)
                )
            ],
            forecast=ForecastConfig(
                model="arome_france_hd",
                hourly_vars="wind_speed_10m,wind_direction_10m",
                wave_vars="wave_height",
                forecast_hours_hourly=48,
                forecast_min15=24,
            ),
            time_window=TimeWindow(day_start=6, day_end=20),
            conditions=Conditions(
                bands=[
                    ["too much", 40],
                    ["hardcore", 35],
                    ["good", 20],
                    ["light", 12],
                ],
                rain_limit=-1.0,  # Negative rain limit
            ),
        )

    # Test invalid wind bands (non-decreasing speeds)
    with pytest.raises(ValueError, match="Band thresholds must be in strictly descending order"):
        invalid_config = WindConfig(
            spots=[
                WindSpot(
                    name="spot1", lat=43.5, lon=3.9, dir_sector=DirectionSector(start=90, end=180)
                )
            ],
            forecast=ForecastConfig(
                model="arome_france_hd",
                hourly_vars="wind_speed_10m,wind_direction_10m",
                wave_vars="wave_height",
                forecast_hours_hourly=48,
                forecast_min15=24,
            ),
            time_window=TimeWindow(day_start=6, day_end=20),
            conditions=Conditions(
                bands=[
                    ["too much", 40],
                    ["hardcore", 35],
                    ["good", 20],
                    ["light", 25],  # Speed greater than previous band
                ],
                rain_limit=2.0,
            ),
        )

    # Test empty wind bands
    with pytest.raises(ValueError, match="Must provide at least one band"):
        invalid_config = WindConfig(
            spots=[
                WindSpot(
                    name="spot1", lat=43.5, lon=3.9, dir_sector=DirectionSector(start=90, end=180)
                )
            ],
            forecast=ForecastConfig(
                model="arome_france_hd",
                hourly_vars="wind_speed_10m,wind_direction_10m",
                wave_vars="wave_height",
                forecast_hours_hourly=48,
                forecast_min15=24,
            ),
            time_window=TimeWindow(day_start=6, day_end=20),
            conditions=Conditions(bands=[], rain_limit=2.0),  # Empty bands list
        )

    # Test invalid band format
    with pytest.raises(ValueError):
        invalid_config = WindConfig(
            spots=[
                WindSpot(
                    name="spot1", lat=43.5, lon=3.9, dir_sector=DirectionSector(start=90, end=180)
                )
            ],
            forecast=ForecastConfig(
                model="arome_france_hd",
                hourly_vars="wind_speed_10m,wind_direction_10m",
                wave_vars="wave_height",
                forecast_hours_hourly=48,
                forecast_min15=24,
            ),
            time_window=TimeWindow(day_start=6, day_end=20),
            conditions=Conditions(
                bands=[
                    ["too much", "invalid"],  # Speed as non-numeric string
                    ["hardcore", 35],
                    ["good", 20],
                    ["light", 12],
                ],
                rain_limit=2.0,
            ),
        )
