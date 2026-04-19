"""Test command-line interface."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from windforecast.cli import main, parse_args


def test_parse_args_defaults():
    """Test argument parsing with default values."""
    with patch("sys.argv", ["windforecast"]):
        args = parse_args()
        assert args.config is None
        assert args.out_dir == Path("out")
        assert not args.verbose


def test_parse_args_custom():
    """Test argument parsing with custom values."""
    with patch(
        "sys.argv",
        ["windforecast", "--config", "custom_config.json", "--out-dir", "custom_out", "--verbose"],
    ):
        args = parse_args()
        assert args.config == Path("custom_config.json")
        assert args.out_dir == Path("custom_out")
        assert args.verbose


@pytest.fixture
def mock_dependencies(tmp_path):
    """Mock external dependencies."""
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "spots": [
                    {
                        "name": "Test Spot",
                        "lat": 41.3948,
                        "lon": 2.2105,
                        "dir_sector": {"start": 225, "end": 45, "wrap": True},
                    }
                ],
                "forecast": {
                    "model": "test_model",
                    "hourly_vars": "wind_speed_10m",
                    "wave_vars": "wave_height",
                    "forecast_hours_hourly": 24,
                    "forecast_min15": 12,
                },
                "time_window": {"day_start": 6, "day_end": 20},
                "conditions": {"bands": [["good", 17], ["light", 12]], "rain_limit": 0.5},
            }
        )
    )
    out_dir = tmp_path / "out"

    # Mock forecast data
    forecast_data = {
        "generated_at": "2024-03-14T12:00:00Z",
        "spots": [
            {
                "spot": "Test Spot",
                "rows": [
                    {
                        "time": "2024-03-14T12:00:00Z",
                        "wind_kn": 15.5,
                        "gust_kn": 20.1,
                        "dir_deg": 240.0,
                        "dir": "WSW",
                        "precip_mm_h": 0.0,
                        "wave_m": 1.2,
                        "band": "good",
                        "kiteable": True,
                    }
                ],
            }
        ],
    }

    return {"config_file": config_file, "out_dir": out_dir, "forecast_data": forecast_data}


def test_main_successful_run(mock_dependencies):
    """Test successful execution of main function."""
    with (
        patch(
            "sys.argv",
            [
                "windforecast",
                "--config",
                str(mock_dependencies["config_file"]),
                "--out-dir",
                str(mock_dependencies["out_dir"]),
            ],
        ),
        patch("windforecast.cli.ForecastClient") as MockClient,
        patch("windforecast.cli.ReportRenderer") as MockRenderer,
    ):

        # Setup mocks
        mock_client = MagicMock()
        mock_client.fetch_forecasts.return_value = mock_dependencies["forecast_data"]
        MockClient.return_value = mock_client

        mock_renderer = MagicMock()
        MockRenderer.return_value = mock_renderer

        # Run main
        result = main()

        # Verify
        assert result == 0
        mock_client.fetch_forecasts.assert_called_once()
        mock_renderer.render_html.assert_called_once()
        assert mock_dependencies["out_dir"].exists()
        assert (mock_dependencies["out_dir"] / "windows.json").exists()


def test_main_config_error(tmp_path):
    """Test main function with invalid config."""
    config_file = tmp_path / "invalid_config.json"
    config_file.write_text("invalid json")

    with patch("sys.argv", ["windforecast", "--config", str(config_file), "--verbose"]):
        result = main()
        assert result == 1


# --- plot subcommand ---


def test_parse_args_plot_spot():
    with patch("sys.argv", ["windforecast", "plot", "--spot", "Bogatell"]):
        args = parse_args()
    assert args.cmd == "plot"
    assert args.spot == "Bogatell"
    assert not args.all


def test_parse_args_plot_all():
    with patch("sys.argv", ["windforecast", "plot", "--all"]):
        args = parse_args()
    assert args.cmd == "plot"
    assert args.all


def test_parse_args_plot_adhoc():
    with patch(
        "sys.argv",
        [
            "windforecast",
            "plot",
            "--lat",
            "41.38",
            "--lon",
            "2.21",
            "--name",
            "My Spot",
            "--no-open",
        ],
    ):
        args = parse_args()
    assert args.lat == 41.38
    assert args.lon == 2.21
    assert args.name == "My Spot"
    assert args.no_open


def test_main_plot_by_spot(mock_dependencies):
    with (
        patch(
            "sys.argv",
            [
                "windforecast",
                "plot",
                "--spot",
                "Test Spot",
                "--config",
                str(mock_dependencies["config_file"]),
                "--no-open",
            ],
        ),
        patch("windforecast.plot.plot_spot_15min") as mock_plot,
    ):
        result = main()
    assert result == 0
    mock_plot.assert_called_once_with("Test Spot", 41.3948, 2.2105, Path("out"), open_after=False)


def test_main_plot_all(mock_dependencies):
    with (
        patch(
            "sys.argv",
            [
                "windforecast",
                "plot",
                "--all",
                "--config",
                str(mock_dependencies["config_file"]),
                "--no-open",
            ],
        ),
        patch("windforecast.plot.plot_spot_15min") as mock_plot,
    ):
        result = main()
    assert result == 0
    assert mock_plot.call_count == 1  # one spot in test config


def test_main_plot_invalid_spot(mock_dependencies):
    with patch(
        "sys.argv",
        [
            "windforecast",
            "plot",
            "--spot",
            "Nonexistent",
            "--config",
            str(mock_dependencies["config_file"]),
        ],
    ):
        result = main()
    assert result == 1


def test_main_plot_no_target(mock_dependencies):
    with patch(
        "sys.argv", ["windforecast", "plot", "--config", str(mock_dependencies["config_file"])]
    ):
        result = main()
    assert result == 1


def test_main_forecast_error(mock_dependencies):
    """Test main function when forecast fetching fails."""
    with (
        patch("sys.argv", ["windforecast", "--config", str(mock_dependencies["config_file"])]),
        patch("windforecast.cli.ForecastClient") as MockClient,
    ):

        # Setup mock to raise an error
        mock_client = MagicMock()
        mock_client.fetch_forecasts.side_effect = Exception("API error")
        MockClient.return_value = mock_client

        # Run main
        result = main()

        # Verify
        assert result == 1
