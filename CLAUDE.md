# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Principles

### Think Before Coding
- State assumptions explicitly. If uncertain, ask rather than guess.
- Present multiple interpretations when they exist; don't choose silently.
- Suggest simpler approaches and push back when warranted.

### Simplicity First
- Implement only what was requested — no speculative features or unasked-for flexibility.
- Avoid premature abstractions for single-use code.
- Don't handle impossible error scenarios.
- Rewrite if it could be substantially shorter without losing clarity.

### Surgical Changes
- Modify only what's necessary to address the request.
- Don't refactor unrelated code or fix unbroken things.
- Match existing style even if you'd prefer alternatives.
- Remove only the unused code your changes created, not pre-existing dead code.

### Goal-Driven Execution
- Convert vague requests into verifiable outcomes before starting (e.g., "Add validation" → "Write and pass validation tests").
- Plan multi-step work explicitly with checkpoints.

---

## Package Structure

**All implementation lives under `src/windforecast/`** — never edit root-level `.py` files like `/render.py` or `/windguru.py` (legacy artifacts, not part of the package).

Always use package imports: `from windforecast import X`

The CLI entry point is `windforecast [options]`.

---

## Commands

```bash
# Install for development (Python version pinned via .python-version to 3.11)
uv sync --extra dev
uv run pre-commit install

# Run the tool
uv run windforecast                          # HTML report only
uv run windforecast --jpg                    # + JPG snapshot (requires Chrome)
uv run windforecast --pdf                    # + PDF version
uv run windforecast --config path/to/config.json
uv run windforecast -v                       # verbose/debug

# Tests
uv run pytest                                # all tests + coverage (configured in pyproject.toml)
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

**`cli.py`**: Thin argument parser — delegates everything to `ForecastClient` and `ReportRenderer`.

**`logging.py`**: `configure_logging(verbose=True, log_file=Path(...))` — call before anything else if you need debug output.

**Outputs** go to `out/` (not committed): `report.html`, `report.jpg`, `report.pdf`, `windows.json` (intermediate processed data).

---

## Configuration

`config.json` controls spots, forecast parameters, time windows, and wind bands. Key fields:

```json
{
  "spots": [{ "name": "...", "lat": 0.0, "lon": 0.0, "dir_sector": { "start": 225, "end": 45, "wrap": true } }],
  "forecast": { "model": "arome_france_hd", "forecast_hours_hourly": 48, "forecast_min15": 24 },
  "time_window": { "day_start": 6, "day_end": 21 },
  "conditions": { "bands": [...], "rain_limit": 0.5, "min_run_hours": 2 }
}
```

See `docs/configuration.md` for the full reference.

---

## JPG/PDF Generation

Requires Chrome or Chromium (auto-detected at standard macOS/Linux paths). `wkhtmltopdf` is the fallback. If neither is available, `--jpg` and `--pdf` flags will fail with a clear error.
