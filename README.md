# wind-forecast

A professional wind forecast analyzer and report generator for kitesurfing conditions. Fetches data from AROME HD model and generates interactive HTML reports with JPG snapshots.

## Features

- 🌊 Accurate wind forecast analysis for multiple kitesurfing spots
- 📊 Interactive HTML reports with detailed forecast visualization
- ⭐ Simple star rating system (1-5 stars) for wind conditions
- 📱 JPG snapshots for mobile viewing and sharing
- ⚙️ Robust configuration with validation
- 📈 Support for both hourly and 15-minute AROME HD forecasts
- 🌡️ Wave height and precipitation integration
- 🔍 Smart kiteable conditions detection
- 📝 Detailed logging and error reporting

## Project Structure

```text
wind-forecast/
├── src/                    # Source code
│   └── windforecast/      # Main package
│       ├── __init__.py    # Package metadata
│       ├── cli.py         # Command-line interface
│       ├── config.py      # Configuration management
│       ├── forecast.py    # Forecast data fetching
│       ├── logging.py     # Logging configuration
│       ├── render.py      # Report generation
│       └── schemas.py     # Data validation models
├── tests/                 # Test suite
│   ├── conftest.py       # Test fixtures
│   ├── test_config.py    # Config tests
│   ├── test_forecast.py  # Forecast tests
│   └── test_render.py    # Rendering tests
├── docs/                  # Documentation
│   └── configuration.md   # Config guide
├── config.json           # Main configuration
├── .pre-commit-config.yaml # Development hooks
├── pyproject.toml        # Project metadata
└── README.md            # This file
```

## Quick Start

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```

2. Install with development tools:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run the forecast analyzer:
   ```bash
   windforecast --jpg
   ```

## Installation Options

### For Users

```bash
# Basic installation
pip install .

# With optional image handling
pip install .[pillow]
```

### For Developers

```bash
# Full development installation
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Usage

After installation, run the tool with:

```bash
# Basic usage
windforecast

# Generate JPG snapshot
windforecast --jpg

# Custom configuration
windforecast --config path/to/config.json

# Debug output
windforecast -v

# Show version
windforecast --version
```

## Configuration

The tool uses a JSON configuration file to define:

- Kite spots and their valid wind sectors
- Forecast parameters and time ranges
- Time window restrictions (e.g., daylight hours)
- Wind band thresholds and conditions

Example:
```json
{
  "spots": [{
    "name": "Beach Spot",
    "lat": 41.3948,
    "lon": 2.2105,
    "dir_sector": {
      "start": 225,
      "end": 45,
      "wrap": true
    }
  }],
  "forecast": {
    "model": "arome_france_hd",
    "hourly_vars": "wind_speed_10m,wind_direction_10m",
    "wave_vars": "wave_height",
    "forecast_hours_hourly": 48,
    "forecast_min15": 24
  }
}
```

See [docs/configuration.md](docs/configuration.md) for complete configuration guide.

## Development

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=windforecast

# HTML coverage report
pytest --cov=windforecast --cov-report=html
```

### Code Quality

The project uses pre-commit hooks for:
- Black code formatting
- isort import sorting
- MyPy type checking
- Basic file hygiene

### Logging

Comprehensive logging with configurable levels:

```python
from windforecast.logging import configure_logging

# Debug output
configure_logging(verbose=True)

# With file output
configure_logging(log_file=Path("wind.log"))
```

## Requirements

### Python Dependencies
- Core:
  - pandas: Data processing
  - requests: API access
  - pydantic: Config validation
- Optional:
  - pillow: Better image handling

### HTML to JPG Conversion
The tool will automatically detect and use:
1. **Chrome/Chromium** (recommended)
   - Uses system-installed Chrome or Chromium
   - Automatically detected in standard locations:
     - macOS: `/Applications/Google Chrome.app` or `/Applications/Chromium.app`
     - Linux/Windows: Available in system PATH
   - Install if needed:
     - macOS: `brew install --cask google-chrome` or `brew install --cask chromium`
     - Linux: `sudo apt install chromium-browser`
2. **wkhtmltopdf** (fallback)
   - macOS: `brew install wkhtmltopdf`
   - Linux: `sudo apt install wkhtmltopdf`

### Contributors

- Pierre Malafosse (maintainer)

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0). This means you can share and adapt the code, but commercial use is not permitted. See the [LICENSE](LICENSE) file for details.
