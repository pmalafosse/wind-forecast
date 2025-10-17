"""Logging configuration for the wind forecast application."""

import json
import logging.config
import sys
from pathlib import Path
from typing import Optional


def configure_logging(verbose: bool = False, log_file: Optional[Path] = None) -> None:
    """
    Configure logging for the application.

    Args:
        verbose: If True, sets root logger to DEBUG level
        log_file: Optional path to log file. If provided, adds a file handler.
    """
    from typing import Any, Dict, List

    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {"format": "%(levelname)s: %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG" if verbose else "INFO",
                "formatter": "standard",
                "stream": sys.stdout,
            }
        },
        "loggers": {
            "windforecast": {  # Root package logger
                "level": "DEBUG" if verbose else "INFO",
                "handlers": ["console"],
                "propagate": False,
            }
        },
        "root": {"level": "WARNING", "handlers": ["console"]},  # For all other loggers
    }

    if log_file:
        # Add file handler if log_file is specified
        config["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": str(log_file),
            "mode": "a",
        }
        if isinstance(config["loggers"]["windforecast"]["handlers"], list):
            config["loggers"]["windforecast"]["handlers"].append("file")

    # Apply configuration
    logging.config.dictConfig(config)
