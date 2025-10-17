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
            data = json.load(f)

        # Validate and create config object
        config = WindConfig.model_validate(data)

        # Log validation success
        logger.info(f"Loaded configuration with {len(config.spots)} spots")
        for spot in config.spots:
            logger.debug(f"  - {spot.name} ({spot.lat}, {spot.lon})")

        return config

    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in config file: {e}"
        logger.error(msg)
        raise ValueError(msg) from e

    except ValidationError as e:
        msg = f"Invalid configuration:\n" + "\n".join(
            f"  - {err['loc']}: {err['msg']}" for err in e.errors()
        )
        logger.error(msg)
        raise ValueError(msg) from e

    except Exception as e:
        msg = f"Error loading config: {e}"
        logger.error(msg)
        raise ValueError(msg) from e
