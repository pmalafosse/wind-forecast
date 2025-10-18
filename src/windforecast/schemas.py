"""Data schemas and validation for wind forecast data."""

from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, Field, validator
from pydantic.types import PositiveInt, confloat


class DirectionSector(BaseModel):
    """Wind direction sector configuration."""

    start: float = Field(ge=0, le=360)  # degrees
    end: float = Field(ge=0, le=360)  # degrees
    wrap: bool = False  # whether sector wraps around north

    @validator("end")
    def validate_sector(cls, v: float, values: dict) -> float:
        """Validate that start and end create a valid sector."""
        if "start" not in values:
            return v
        start = values["start"]
        if not values.get("wrap", False):  # Default to False if wrap is not set yet
            if start > v:
                # Convert sector to use larger end value
                return v + 360 if start > v else v
        return v


class WindSpot(BaseModel):
    """A kitesurfing spot with its location and wind direction constraints."""

    name: str
    lat: float = Field(ge=-90, le=90)  # latitude
    lon: float = Field(ge=-180, le=180)  # longitude
    dir_sector: DirectionSector

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Example Beach",
                "lat": 41.3948,
                "lon": 2.2105,
                "dir_sector": {"start": 225, "end": 45, "wrap": True},
            }
        }


class ForecastConfig(BaseModel):
    """Forecast retrieval configuration."""

    model: str = Field(default="arome_france_hd", pattern="^[a-z_]+$")
    hourly_vars: str = Field(pattern="^[a-z_0-9]+(,[a-z_0-9]+)*$")
    wave_vars: str = Field(pattern="^[a-z_0-9]+(,[a-z_0-9]+)*$")
    forecast_hours_hourly: PositiveInt = Field(le=48)  # AROME HD limit
    forecast_min15: PositiveInt = Field(le=24)  # 15-min forecast limit


class TimeWindow(BaseModel):
    """Time window configuration for daylight hours."""

    day_start: float = Field(ge=0, le=23, description="Hour to start considering forecasts")
    day_end: float = Field(ge=0, le=23, description="Hour to stop considering forecasts")

    @validator("day_end")
    def validate_window(cls, v: float, values: dict) -> float:
        """Validate that end time is after start time."""
        if "day_start" in values and v < values["day_start"]:
            raise ValueError("day_end must be after day_start")
        return v


class Conditions(BaseModel):
    """Wind conditions and thresholds."""

    bands: List[Tuple[str, float]] = Field(description="Wind speed bands and their thresholds")
    rain_limit: float = Field(ge=0, description="Maximum acceptable precipitation rate in mm/h")

    @validator("bands")
    def validate_bands(cls, v: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """Validate that bands are in descending order."""
        if not v:
            raise ValueError("Must provide at least one band")
        thresholds = [band[1] for band in v]
        if not all(x > y for x, y in zip(thresholds[:-1], thresholds[1:])):
            raise ValueError("Band thresholds must be in strictly descending order")
        return v


class WindConfig(BaseModel):
    """Complete wind forecasting configuration."""

    spots: List[WindSpot] = Field(min_items=1)
    forecast: ForecastConfig
    time_window: TimeWindow
    conditions: Conditions

    class Config:
        json_schema_extra = {
            "example": {
                "spots": [
                    {
                        "name": "Example Beach",
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
                    "bands": [["too much", 40], ["good", 17], ["light", 12]],
                    "rain_limit": 0.5,
                },
            }
        }
