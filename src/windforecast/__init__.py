"""Wind forecast analyzer and report generator for kitesurfing conditions."""

try:
    from importlib.metadata import PackageNotFoundError, version  # type: ignore
except ImportError:
    # Python < 3.8
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

try:
    __version__ = version("windforecast")
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.0"
