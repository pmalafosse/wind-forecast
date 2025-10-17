"""Test forecast data fetching and processing."""

import json
from unittest.mock import Mock, patch

import pytest

from windforecast.config import load_config
from windforecast.forecast import ForecastClient


def test_forecast_client_init(config_file):
    """Test ForecastClient initialization."""
    config = load_config(config_file)
    client = ForecastClient(config)
    assert client.config == config
    assert client.base_url == "https://api.open-meteo.com/v1/meteofrance"
    assert client.marine_url == "https://marine-api.open-meteo.com/v1/marine"


@pytest.mark.parametrize(
    "status_code,expected_error",
    [
        (404, "HTTP Error 404"),
        (500, "HTTP Error 500"),
        (403, "HTTP Error 403"),
    ],
)
def test_fetch_forecasts_api_error(config_file, status_code, expected_error):
    """Test error handling for API failures."""
    config = load_config(config_file)
    client = ForecastClient(config)

    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.raise_for_status.side_effect = Exception(expected_error)

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(Exception, match=expected_error):
            client.fetch_forecasts()


def test_process_forecasts(config_file, sample_forecast_data, sample_wave_data):
    """Test forecast data processing."""
    config = load_config(config_file)
    client = ForecastClient(config)

    # Mock API responses
    with patch("requests.get") as mock_get:
        mock_responses = [
            Mock(json=lambda: sample_forecast_data),
            Mock(json=lambda: sample_forecast_data),  # 15min data
            Mock(json=lambda: sample_wave_data),
            Mock(json=lambda: {"arome_france_hd": {"run": "2024-03-14T12:00:00Z"}}),
        ]
        mock_get.side_effect = mock_responses

        result = client.fetch_forecasts()

        assert isinstance(result, dict)
        assert "generated_at" in result
        assert "model_updates" in result
        assert "spots" in result

        # Check that we have data for each spot
        spot_names = [spot["name"] for spot in config.spots]
        result_names = [spot["spot"] for spot in result["spots"]]
        assert result_names == spot_names
