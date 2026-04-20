"""Tests for advanced rendering features."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytz

from windforecast.render import ReportRenderer


def test_model_info_generation():
    """Test model information section generation."""
    renderer = ReportRenderer()
    data = {
        "spots": [],
        "model_updates": {
            "model1": {
                "title": "Test Model",
                "run": "2025-10-19T12:00:00Z",
            }
        },
        "generated_at": "2025-10-19T12:30:00Z",
        "config": {
            "conditions": {
                "bands": [
                    ["too much", 40],
                    ["hardcore", 35],
                    ["good", 20],
                    ["light", 12],
                ]
            }
        },
    }

    output_path = Path("/tmp/test.html")
    tz_paris = pytz.timezone("Europe/Paris")

    with (
        patch("pathlib.Path.write_text") as mock_write,
        patch(
            "builtins.open",
            return_value=MagicMock(
                __enter__=MagicMock(
                    return_value=MagicMock(
                        read=MagicMock(
                            return_value="<!-- FORECAST_DATA --><!-- GENERATED_AT --><!-- MODEL_UPDATES -->"
                        )
                    )
                )
            ),
        ),
        patch("pytz.timezone", return_value=tz_paris),
    ):
        renderer.render_html(data, output_path)
        written_content = mock_write.call_args[0][0]
        assert "Test Model" in written_content
        assert "2025-10-19 12:00" in written_content
        assert "UTC" in written_content
