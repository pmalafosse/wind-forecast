# Configuration Guide

The wind forecast application uses a JSON configuration file (`config.json`) to define:
- Kite spots and their characteristics
- Forecast parameters
- Time window restrictions
- Wind condition thresholds

## Configuration File Structure

```json
{
  "spots": [
    {
      "name": "Example Beach",
      "lat": 41.3948,
      "lon": 2.2105,
      "dir_sector": {
        "start": 225,
        "end": 45,
        "wrap": true
      }
    }
  ],
  "forecast": {
    "model": "arome_france_hd",
    "hourly_vars": "wind_speed_10m,wind_direction_10m",
    "wave_vars": "wave_height",
    "forecast_hours_hourly": 48,
    "forecast_min15": 24
  },
  "time_window": {
    "day_start": 6,
    "day_end": 20
  },
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
      ["below", 0]
    ],
    "rain_limit": 0.5,
    "min_run_hours": 2.0
  }
}
```

## Section Details

### Spots
Each spot requires:
- `name`: Display name for the spot
- `lat`: Latitude (-90 to 90)
- `lon`: Longitude (-180 to 180)
- `dir_sector`: Valid wind direction range
  - `start`: Starting angle in degrees (0-360)
  - `end`: Ending angle in degrees (0-360)
  - `wrap`: Whether the sector wraps around north (e.g., 315° to 45°)

### Forecast
AROME forecast configuration:
- `model`: Currently only supports `"arome_france_hd"`
- `hourly_vars`: Comma-separated list of hourly variables
- `wave_vars`: Comma-separated list of wave variables
- `forecast_hours_hourly`: Hours to forecast (max 48)
- `forecast_min15`: 15-minute forecast period (max 24)

### Time Window
Restrict analysis to daylight hours:
- `day_start`: Hour to start considering forecasts (0-23)
- `day_end`: Hour to end considering forecasts (0-23)

### Conditions
Define wind thresholds and limits:
- `bands`: List of [name, threshold] pairs in descending order
- `rain_limit`: Maximum acceptable precipitation (mm/h)
- `min_run_hours`: Minimum consecutive hours for a session

## Validation

The configuration file is validated on load to ensure:
- All required fields are present
- Values are within valid ranges
- Wind direction sectors are valid
- Time window makes sense
- Bands are in descending order
- Data types are correct

## Example Spots

### Beach Spot Example
```json
{
  "name": "Beach Spot",
  "lat": 41.3948,
  "lon": 2.2105,
  "dir_sector": {
    "start": 225,
    "end": 45,
    "wrap": true
  }
}
```
This configuration is suitable for a beach spot that works with winds:
- Coming from SW (225°) through W and N to NE (45°)
- `wrap: true` because the sector crosses north (360°/0°)

### Bay Spot Example
```json
{
  "name": "Bay Spot",
  "lat": 42.85,
  "lon": 3.13,
  "dir_sector": {
    "start": 180,
    "end": 270,
    "wrap": false
  }
}
```
This configuration works for a bay spot that:
- Works with winds from S (180°) to W (270°)
- `wrap: false` because it's a continuous sector
