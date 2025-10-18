"""Configuration management for the wind forecast application."""

import json
import logging
from pathlib import Path
from typing import Optional, Union

from pydantic import ValidationError

from .schemas import WindConfig

logger = logging.getLogger(__name__)


def find_config_file() -> Optional[Path]:
    """
    Search for config.json in standard locations.

    Returns:
        Path to config.json if found, None otherwise.
    """
    search_paths = [Path.cwd() / "config.json", Path(__file__).parent.parent / "config.json"]
    for path in search_paths:
        if path.exists():
            return path
    return None


def load_config(config_path: Optional[Union[Path, str]] = None) -> WindConfig:
    """
    Load and validate configuration from a JSON file.

    Args:
        config_path: Path to config.json. If None, looks in standard locations.

    Returns:
        WindConfig object with validated configuration.

    Raises:
        FileNotFoundError: If config file cannot be found.
        ValueError: If config file contains invalid data.
    """
    # Resolve config path
    if config_path is None:
        config_path = find_config_file()
        if config_path is None:
            raise FileNotFoundError("Could not find config.json")
    else:
        config_path = Path(config_path)

    logger.debug(f"Loading config from {config_path}")

    try:
        with open(config_path, encoding="utf-8") as f:
            try:
                data = json.load(f)
                logger.debug(f"Loaded configuration data: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON in config file: {e}"
                logger.error(msg)
                raise ValueError(msg) from e

        # Validate and create config object
        try:
            config = WindConfig.model_validate(data)
            # Log validation success
            logger.info(f"Loaded configuration with {len(config.spots)} spots")
            for spot in config.spots:
                logger.debug(f"  - {spot.name} ({spot.lat}, {spot.lon})")
            return config
        except ValidationError as e:
            # Extract error details
            error = e.errors()[0]  # Get the first error
            logger.debug(f"Validation error: {error}")

            # Map error types to expected messages
            error_type = error.get("type", "")
            error_msg = error.get("msg", "")
            error_ctx = error.get("ctx", {})

            if error_type == "less_than_equal":
                msg = f"Input should be less than or equal to {error_ctx.get('le', '')}"
            elif error_type == "greater_than_equal":
                msg = f"Input should be greater than or equal to {error_ctx.get('ge', '')}"
            elif error_type == "greater_than":
                msg = f"Input should be greater than {error_ctx.get('gt', '')}"
            elif error_type == "value_error":
                if "day_end must be after day_start" in error_msg:
                    msg = "day_end must be after day_start"
                elif "Band thresholds must be in strictly descending order" in error_msg:
                    msg = "Band thresholds must be in strictly descending order"
                else:
                    msg = error_msg
            else:
                msg = error_msg

            logger.error(
                f"Invalid configuration at {' -> '.join(str(x) for x in error['loc'])}: {msg}"
            )
            raise ValueError(msg)

    except FileNotFoundError as e:
        logger.error(f"Config file not found: {e}")
        raise  # Re-raise FileNotFoundError directly
