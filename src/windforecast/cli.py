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


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.json (default: looks in current and package directory)",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("out"), help="Output directory (default: ./out)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")


def _cmd_report(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
        out_dir = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Fetching forecast data...")
        client = ForecastClient(config)
        data = client.fetch_forecasts()

        json_path = out_dir / "windows.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Wrote {json_path}")

        logger.info("Generating reports...")
        renderer = ReportRenderer()

        html_path = out_dir / "report.html"
        renderer.render_html(data, html_path)
        logger.info(f"Wrote {html_path}")

        if getattr(args, "plot", False):
            from .plot import plot_spot_from_rows

            model_run = (
                data.get("model_updates", {})
                .get("meteofrance_arome_france_hd_15min", {})
                .get("run")
            )
            for spot_data in data["spots"]:
                plot_spot_from_rows(
                    spot_data["spot"],
                    spot_data.get("min15_rows", []),
                    model_run,
                    out_dir,
                    open_after=not getattr(args, "no_open", True),
                )

        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Detailed error:")
        return 1


def _cmd_plot(args: argparse.Namespace) -> int:
    try:
        # Lazy import so matplotlib absence only fails on `plot` subcommand, not report
        from .plot import plot_spot_15min  # noqa: PLC0415

        config = load_config(args.config)

        if args.all:
            for spot in config.spots:
                plot_spot_15min(spot.name, spot.lat, spot.lon, args.out_dir, open_after=False)
            return 0

        # Resolve single spot: by name from config, or ad-hoc via --lat/--lon
        if args.spot:
            match = next((s for s in config.spots if s.name.lower() == args.spot.lower()), None)
            if match is None:
                names = ", ".join(s.name for s in config.spots)
                logger.error(f"Spot '{args.spot}' not found in config. Available: {names}")
                return 1
            name, lat, lon = match.name, match.lat, match.lon
        elif args.lat is not None and args.lon is not None:
            name = args.name or f"{args.lat},{args.lon}"
            lat, lon = args.lat, args.lon
        else:
            logger.error("Provide --spot NAME, --all, or --lat/--lon for an ad-hoc spot.")
            return 1

        plot_spot_15min(name, lat, lon, args.out_dir, open_after=not args.no_open)
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Detailed error:")
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wind forecast tool for kitesurfing conditions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"windforecast {__version__}")
    _add_common_args(parser)
    parser.add_argument(
        "--plot", action="store_true", help="Also generate 15-min wind charts for all spots"
    )
    parser.add_argument(
        "--no-open", action="store_true", help="Don't open generated plots (used with --plot)"
    )
    parser.set_defaults(cmd="report")

    subparsers = parser.add_subparsers(dest="cmd")

    # 'plot' subcommand
    plot_p = subparsers.add_parser("plot", help="Plot 15-min AROME wind forecast for a spot")
    _add_common_args(plot_p)
    spot_group = plot_p.add_mutually_exclusive_group()
    spot_group.add_argument("--spot", metavar="NAME", help="Spot name from config.json")
    spot_group.add_argument("--all", action="store_true", help="Plot all spots from config.json")
    plot_p.add_argument("--name", metavar="NAME", help="Display name for ad-hoc spot")
    plot_p.add_argument("--lat", type=float, help="Latitude (ad-hoc spot)")
    plot_p.add_argument("--lon", type=float, help="Longitude (ad-hoc spot)")
    plot_p.add_argument("--no-open", action="store_true", help="Don't open the image after saving")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    if args.cmd == "plot":
        return _cmd_plot(args)
    return _cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
