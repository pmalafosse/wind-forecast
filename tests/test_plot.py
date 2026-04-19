"""Tests for forecast plotting utilities."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from windforecast.config import load_config
from windforecast.forecast import ForecastClient, fetch_model_run

# --- fetch_model_run ---


def test_fetch_model_run_success():
    mock_resp = Mock()
    mock_resp.json.return_value = {"reference_time": "2024-03-14T06:00:00Z"}
    with patch("windforecast.forecast.requests.get", return_value=mock_resp):
        result = fetch_model_run()
    assert result == "2024-03-14T06:00:00Z"


def test_fetch_model_run_network_error():
    with patch("windforecast.forecast.requests.get", side_effect=Exception("timeout")):
        result = fetch_model_run()
    assert result is None


def test_fetch_model_run_missing_key():
    mock_resp = Mock()
    mock_resp.json.return_value = {}
    with patch("windforecast.forecast.requests.get", return_value=mock_resp):
        result = fetch_model_run()
    assert result is None


# --- ForecastClient.fetch_spot_15min ---

MIN15_RESPONSE = {
    "minutely_15": {
        "time": ["2024-03-14T12:00", "2024-03-14T12:15"],
        "wind_speed_10m": [14.0, 15.0],
        "wind_gusts_10m": [18.0, 19.5],
        "wind_direction_10m": [240, 245],
        "precipitation": [0.0, 0.0],
    }
}


def test_fetch_spot_15min_returns_rows(config_file):
    config = load_config(config_file)
    client = ForecastClient(config)

    mock_resp = Mock()
    mock_resp.json.return_value = MIN15_RESPONSE
    with patch("windforecast.forecast.requests.get", return_value=mock_resp):
        rows = client.fetch_spot_15min(41.38, 2.21)

    assert len(rows) == 2
    assert rows[0]["time"] == "2024-03-14T12:00"
    assert rows[0]["wind_kn"] == 14.0
    assert rows[0]["gust_kn"] == 18.0
    assert rows[0]["dir_deg"] == 240


def test_fetch_spot_15min_api_error(config_file):
    config = load_config(config_file)
    client = ForecastClient(config)

    mock_resp = Mock()
    mock_resp.raise_for_status.side_effect = Exception("HTTP 500")
    with patch("windforecast.forecast.requests.get", return_value=mock_resp):
        with pytest.raises(Exception, match="HTTP 500"):
            client.fetch_spot_15min(41.38, 2.21)


# --- plot_spot_15min ---


@pytest.fixture(autouse=True, scope="module")
def agg_backend():
    """Use non-interactive Agg backend so tests don't open windows."""
    import matplotlib

    matplotlib.use("Agg")


def test_plot_spot_15min_saves_to_plots_subdir(tmp_path, config_file):
    rows = [
        {"time": "2024-03-14T12:00", "wind_kn": 14.0, "gust_kn": 18.0, "dir_deg": 240},
        {"time": "2024-03-14T12:15", "wind_kn": 15.0, "gust_kn": 19.0, "dir_deg": 242},
    ]

    with (
        patch("windforecast.config.load_config", return_value=load_config(config_file)),
        patch("windforecast.forecast.ForecastClient") as MockClient,
        patch("windforecast.forecast.fetch_model_run", return_value="2024-03-14T06:00:00Z"),
        patch("windforecast.plot.datetime") as mock_dt,
        patch("windforecast.plot.subprocess.run"),
    ):

        mock_dt.now.return_value.date.return_value = __import__("datetime").date(2024, 3, 14)
        mock_dt.fromisoformat.side_effect = __import__("datetime").datetime.fromisoformat
        MockClient.return_value.fetch_spot_15min.return_value = rows

        from windforecast.plot import plot_spot_15min

        out_path = plot_spot_15min("Test Spot", 41.38, 2.21, tmp_path, open_after=False)

    assert out_path == tmp_path / "plots" / "test_spot_15min_today.png"
    assert out_path.exists()


def test_plot_spot_15min_no_data_today_exits(tmp_path, config_file):
    rows = [{"time": "2023-01-01T12:00", "wind_kn": 14.0, "gust_kn": 18.0, "dir_deg": 240}]

    with (
        patch("windforecast.config.load_config", return_value=load_config(config_file)),
        patch("windforecast.forecast.ForecastClient") as MockClient,
        patch("windforecast.forecast.fetch_model_run", return_value=None),
    ):

        MockClient.return_value.fetch_spot_15min.return_value = rows

        from windforecast.plot import plot_spot_15min

        with pytest.raises(SystemExit):
            plot_spot_15min("Test Spot", 41.38, 2.21, tmp_path, open_after=False)
