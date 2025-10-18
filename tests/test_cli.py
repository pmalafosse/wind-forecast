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
        assert not args.jpg
        assert not args.verbose


def test_parse_args_custom():
    """Test argument parsing with custom values."""
    with patch(
        "sys.argv",
        [
            "windforecast",
            "--config",
            "custom_config.json",
            "--out-dir",
            "custom_out",
            "--jpg",
            "--verbose",
        ],
    ):
        args = parse_args()
        assert args.config == Path("custom_config.json")
        assert args.out_dir == Path("custom_out")
        assert args.jpg
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
    with patch(
        "sys.argv",
        [
            "windforecast",
            "--config",
            str(mock_dependencies["config_file"]),
            "--out-dir",
            str(mock_dependencies["out_dir"]),
        ],
    ), patch("windforecast.cli.ForecastClient") as MockClient, patch(
        "windforecast.cli.ReportRenderer"
    ) as MockRenderer:

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


def test_main_with_jpg(mock_dependencies):
    """Test main function with JPG generation."""
    with patch(
        "sys.argv",
        [
            "windforecast",
            "--config",
            str(mock_dependencies["config_file"]),
            "--out-dir",
            str(mock_dependencies["out_dir"]),
            "--jpg",
        ],
    ), patch("windforecast.cli.ForecastClient") as MockClient, patch(
        "windforecast.cli.ReportRenderer"
    ) as MockRenderer:

        # Setup mocks
        mock_client = MagicMock()
        mock_client.fetch_forecasts.return_value = mock_dependencies["forecast_data"]
        MockClient.return_value = mock_client

        mock_renderer = MagicMock()
        mock_renderer.generate_jpg.return_value = True
        MockRenderer.return_value = mock_renderer

        # Run main
        result = main()

        # Verify
        assert result == 0
        mock_renderer.generate_jpg.assert_called_once()
        assert mock_dependencies["out_dir"].exists()


def test_main_jpg_failure(mock_dependencies):
    """Test main function when JPG generation fails."""
    with patch(
        "sys.argv",
        [
            "windforecast",
            "--config",
            str(mock_dependencies["config_file"]),
            "--out-dir",
            str(mock_dependencies["out_dir"]),
            "--jpg",
        ],
    ), patch("windforecast.cli.ForecastClient") as MockClient, patch(
        "windforecast.cli.ReportRenderer"
    ) as MockRenderer:

        # Setup mocks
        mock_client = MagicMock()
        mock_client.fetch_forecasts.return_value = mock_dependencies["forecast_data"]
        MockClient.return_value = mock_client

        mock_renderer = MagicMock()
        mock_renderer.generate_jpg.return_value = False
        MockRenderer.return_value = mock_renderer

        # Run main
        result = main()

        # Verify
        assert result == 1
        mock_renderer.generate_jpg.assert_called_once()


def test_main_config_error(tmp_path):
    """Test main function with invalid config."""
    config_file = tmp_path / "invalid_config.json"
    config_file.write_text("invalid json")

    with patch("sys.argv", ["windforecast", "--config", str(config_file), "--verbose"]):
        result = main()
        assert result == 1


def test_main_forecast_error(mock_dependencies):
    """Test main function when forecast fetching fails."""
    with patch(
        "sys.argv", ["windforecast", "--config", str(mock_dependencies["config_file"])]
    ), patch("windforecast.cli.ForecastClient") as MockClient:

        # Setup mock to raise an error
        mock_client = MagicMock()
        mock_client.fetch_forecasts.side_effect = Exception("API error")
        MockClient.return_value = mock_client

        # Run main
        result = main()

        # Verify
        assert result == 1
