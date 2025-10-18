"""Command-line interface for the wind forecast application."""

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .forecast import ForecastClient
from .logging import configure_logging
from .render import ReportRenderer

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate wind forecast reports for kitesurfing conditions."
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.json (default: looks in current and package directory)",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("out"), help="Output directory (default: ./out)"
    )
    parser.add_argument("--jpg", action="store_true", help="Generate JPG snapshot of the report")
    parser.add_argument(
        "--summary", action="store_true", help="Include daily summary section in the report"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="version", version=f"windforecast {__version__}")
    return parser.parse_args()


def main() -> int:
    """Main entry point for the application."""
    args = parse_args()
    configure_logging(args.verbose)

    try:
        # Load configuration
        config = load_config(args.config)

        # Create output directory
        out_dir = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        # Fetch forecast data
        logger.info("Fetching forecast data...")
        client = ForecastClient(config)
        data = client.fetch_forecasts()

        # Save intermediate JSON
        json_path = out_dir / "windows.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Wrote {json_path}")

        # Generate reports
        logger.info("Generating reports...")
        renderer = ReportRenderer()

        html_path = out_dir / "report.html"
        renderer.render_html(data, html_path, include_summary=args.summary)
        logger.info(f"Wrote {html_path}")

        if args.jpg:
            jpg_path = out_dir / "report.jpg"
            if renderer.generate_jpg(html_path, jpg_path):
                logger.info(f"Wrote {jpg_path}")
            else:
                logger.error("Failed to generate JPG")
                return 1

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Detailed error:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
