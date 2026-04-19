"""Wind forecast analyzer and report generator for kitesurfing conditions."""

# Initialize version to fallback
__version__ = "0.0.0"

# First try importlib.metadata (Python ≥ 3.8)
try:
    from importlib.metadata import PackageNotFoundError, version  # type: ignore

    try:
        __version__ = version("windforecast")
    except PackageNotFoundError:
        # Keep fallback version
        pass
except ImportError:
    # Python < 3.8, try importlib_metadata
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

    try:
        __version__ = version("windforecast")
    except PackageNotFoundError:
        # Keep fallback version
        pass

from .cli import main
from .config import load_config
from .forecast import get_wind_forecast
from .render import ReportRenderer
from .schemas import WindSpeedThresholds

__all__ = [
    "ReportRenderer",
    "main",
    "load_config",
    "get_wind_forecast",
    "WindSpeedThresholds",
    "__version__",
]
