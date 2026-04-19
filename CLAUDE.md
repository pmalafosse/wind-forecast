# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Principles
- State assumptions explicitly; ask rather than guess when uncertain.
- Remove only unused code your changes created, not pre-existing dead code.

---

## Package Structure

**All implementation lives under `src/windforecast/`** — never edit root-level `.py` files like `/render.py` or `/windguru.py` (legacy artifacts, not part of the package).

Always use package imports: `from windforecast import X`

The CLI entry point is `windforecast [options]`.

---

## Commands

```bash
# Install for development (Python version pinned via .python-version to 3.14)
uv sync --extra dev          # includes pytest, black, mypy, selenium, matplotlib
uv run pre-commit install

# Run the tool
uv run windforecast                          # HTML report
uv run windforecast --config path/to/config.json
uv run windforecast -v                       # verbose/debug

# Plot 15-min AROME forecast (matplotlib included in --extra dev)
uv run windforecast plot --spot Bogatell     # single spot from config.json
uv run windforecast plot --all               # all spots from config.json
uv run windforecast plot --lat 41.38 --lon 2.21 --name "My Spot"  # ad-hoc

# Tests
uv run pytest                                # all tests except selenium (configured in pyproject.toml)
uv run pytest -m selenium                   # selenium/Chrome tests only
uv run pytest tests/test_forecast.py        # single test file
uv run pytest tests/test_render.py::test_name  # single test

# Code quality (also runs on commit via pre-commit)
uv run pre-commit run --all-files
```

Line length is 100 characters (Black + isort configured in `pyproject.toml`).

---

## Architecture

The pipeline runs in sequence: `config.json` → `load_config()` → `ForecastClient.fetch_forecasts()` → `ReportRenderer.render_html()` → output files.

**`config.py` + `schemas.py`**: Loads and validates `config.json` via Pydantic. Key models: `WindConfig`, `WindSpot`, `DirectionSector`. Direction sectors can wrap (cross North), e.g. `start=225, end=45, wrap=true`.

**`forecast.py`**: `ForecastClient` calls the Open-Meteo API (AROME HD model), fetches hourly + 15-min data and wave heights, then returns a processed dict of DataFrames keyed by spot. Kiteable conditions are determined here by checking wind direction falls within the sector, speed is within band thresholds, and precipitation is below `rain_limit`.

**`render.py`**: `ReportRenderer` generates the full HTML report. Wind conditions map to named bands (e.g. `"great"`, `"insane"`, `"hardcore"`, `"too much"`) configured in `config.json` under `conditions.bands`. These drive both star ratings and cell CSS classes. HTML cells follow this pattern:

```html
<td class="cell-data {wind_band} {kiteable|not-kiteable}" data-hour="{hour}" data-kiteable="{true|false}">
```

Report structure uses day sections:

```html
<div class="day-section">
  <h2>{date}</h2>
  <div class="table-container">
    <table class="forecast-table"><!-- ... --></table>
  </div>
</div>
```

**`cli.py`**: Thin argument parser — delegates everything to `ForecastClient` and `ReportRenderer`.

**`logging.py`**: `configure_logging(verbose=True, log_file=Path(...))` — call before anything else if you need debug output.

**Outputs** go to `out/` (not committed): `report.html`, `windows.json` (intermediate processed data), `plots/` (per-spot 15-min charts).

---

## Configuration

`config.json` controls spots, forecast parameters, time windows, and wind bands. Key fields:

```json
{
  "spots": [{ "name": "...", "lat": 0.0, "lon": 0.0, "dir_sector": { "start": 225, "end": 45, "wrap": true } }],
  "forecast": { "model": "arome_france_hd", "forecast_hours_hourly": 48, "forecast_min15": 24 },
  "time_window": { "day_start": 6, "day_end": 21 },
  "conditions": { "bands": [...], "rain_limit": 0.5 }
}
```

See `docs/configuration.md` for the full reference.

---
