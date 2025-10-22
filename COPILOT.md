# Wind Forecast - Copilot Guide

⚠️ CRITICAL PACKAGE STRUCTURE NOTICE ⚠️

This project is structured as a proper Python package. The ONLY valid implementation is in:
```
src/windforecast/
├── __init__.py    # Package metadata
├── cli.py         # Command-line interface
├── config.py      # Configuration management
├── forecast.py    # Forecast data fetching
├── logging.py     # Logging configuration
├── render.py      # Report generation
└── schemas.py     # Data validation models
```

🚫 IMPORTANT: NEVER reference or suggest edits to:
- ❌ /render.py
- ❌ /windguru.py
- ❌ Any other Python files in the root directory

✅ ALWAYS use:
- The package structure under src/windforecast/
- Package imports (from windforecast import X)
- The CLI command: windforecast [options]

## Documentation Sources

For implementation details, ALWAYS refer to:
1. README.md - Authoritative project structure
2. docs/configuration.md - Configuration guide
3. CONTRIBUTING.md - Development workflow

## Project Overview

The windforecast package:
1. Fetches weather data from Open-Meteo API
2. Processes wind conditions for kitesurfing spots
3. Generates interactive HTML reports

## Code Pattern Guidelines

### 1. Wind Data Processing

Wind data processing follows these patterns:
```python
def process_forecast_data(data):
    """Process raw forecast data into daily tables.

    Pattern:
    1. Extract spot data from input
    2. Identify kiteable hours
    3. Group by date and spot
    4. Track kiteable conditions
    """
    spot_rows = {s["spot"]: s["rows"] for s in data["spots"]}
    # ... process data ...
    return daily_tables, spots, model_updates
```

### 2. HTML Report Generation

Report generation uses these patterns:
```python
def render_html(data, output_path):
    """Generate HTML report from forecast data.

    Pattern:
    1. Load template
    2. Process spot data by day
    3. Generate HTML tables
    4. Add interactive features
    """
    # Load template
    template = load_template()
    # ... generate HTML ...
    # Write output
    output_path.write_text(content)
```

### 3. Cell Visibility Logic

HTML cells use these class/attribute patterns:
```html
<td class="cell-data {wind_band} {kiteable_class}"
    data-hour="{hour}"
    data-kiteable="{true|false}">
    <!-- Cell content -->
</td>
```

## Common Development Tasks

### 1. Adding New Features

When adding features:
1. Check existing patterns in related code
2. Follow established naming conventions
3. Update both Python and HTML/JS components
4. Test with sample data

### 2. Modifying Report Layout

When modifying the report:
1. Keep responsive design in mind
2. Maintain visibility toggle functionality
3. Ensure print layout works
4. Test with different data scenarios

### 3. Processing Logic Changes

When changing data processing:
1. Verify kiteable condition logic
2. Maintain spot ordering
3. Handle edge cases (no data, missing values)
4. Update related display logic

## Testing Considerations

Key scenarios to test:
1. No kiteable conditions
2. Mixed kiteable/non-kiteable hours
3. Missing spot data
4. Various wind conditions
5. Different time ranges

## Common Code Locations

1. **Kiteable Conditions Logic**:
   - `windguru.py`: Initial processing
   - `render.py`: Display logic

2. **Report Styling**:
   - `templates/report.html`: CSS definitions
   - Cell classes and data attributes

3. **Interactive Features**:
   - `report.html`: JavaScript functions
   - Toggle and filter functionality

## Project-Specific Notes

1. Use Wind Band Constants:
   ```python
   BANDS = [
       ("too much", 35),
       ("hardcore", 30),
       ("insane", 27),
       # ... etc
   ]
   ```

2. Follow Cell Class Pattern:
   ```python
   cell_class = f"cell-data {wind_band} {'kiteable' if r['kiteable'] else 'not-kiteable'}"
   ```

3. Maintain Report Structure:
   ```html
   <div class="day-section">
     <h2>{date}</h2>
     <div class="table-container">
       <table class="forecast-table">
         <!-- content -->
       </table>
     </div>
   </div>
   ```

## Configuration Patterns

1. Spot Configuration:
   ```json
   {
     "name": "Spot Name",
     "lat": 0.0,
     "lon": 0.0,
     "dir_sector": {
       "start": 0,
       "end": 360,
       "wrap": false
     }
   }
   ```

2. Condition Thresholds:
   ```json
   {
     "conditions": {
       "bands": [...],
       "rain_limit": 0.5,
       "min_run_hours": 2
     }
   }
   ```
