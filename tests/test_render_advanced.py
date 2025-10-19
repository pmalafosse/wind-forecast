"""Tests for advanced rendering features."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytz
from bs4 import BeautifulSoup

from windforecast.render import ReportRenderer
from windforecast.schemas import WindConfig


def test_viewport_calculation():
    """Test viewport size calculation from HTML content."""
    renderer = ReportRenderer()
    html_content = """
    <div class="day-section">
        <table>
            <tr>
                <th>Spot</th>
                <th>09:00</th>
                <th>10:00</th>
            </tr>
            <tr>
                <td>Spot1</td>
                <td>Data1</td>
                <td>Data2</td>
            </tr>
        </table>
    </div>
    """
    width, height = renderer._calculate_viewport(html_content)
    assert width >= 800  # Minimum width
    assert height >= 600  # Minimum height


def test_chrome_finder():
    """Test Chrome executable finder across platforms."""
    renderer = ReportRenderer()

    with patch("sys.platform", "darwin"):
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=True):
                chrome_path = renderer._find_chrome()
                assert chrome_path == "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    with patch("sys.platform", "linux"):
        with patch("shutil.which", return_value="/usr/bin/chromium"):
            chrome_path = renderer._find_chrome()
            assert chrome_path == "/usr/bin/chromium"


@pytest.mark.parametrize(
    "platform,chrome_path,pillow_available,expected",
    [
        ("linux", "/usr/bin/chrome", True, True),
        ("darwin", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", False, True),
        ("linux", "/usr/bin/chrome", False, False),
    ],
)
def test_chrome_image_generation(platform, chrome_path, pillow_available, expected, tmp_path):
    """Test JPG generation using Chrome across different platforms and configurations."""
    html_path = tmp_path / "test.html"
    jpg_path = tmp_path / "test.jpg"
    png_path = jpg_path.with_suffix(".png")
    html_path.write_text("<html><body>Test</body></html>")
    png_path.touch()  # Create empty PNG file

    renderer = ReportRenderer()

    with patch("sys.platform", platform):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("windforecast.render.HAS_PILLOW", pillow_available):
                if pillow_available:
                    with patch("PIL.Image.open") as mock_open:
                        with patch("PIL.Image.Image.convert") as mock_convert:
                            with patch("PIL.Image.Image.save"):
                                mock_img = MagicMock()
                                mock_open.return_value = mock_img
                                mock_convert.return_value = mock_img
                                result = renderer._try_chrome(
                                    chrome_path, html_path, jpg_path, (800, 600)
                                )
                else:
                    with patch("subprocess.run") as mock_run:
                        # Simulate successful sips conversion on macOS
                        mock_run.return_value = MagicMock(returncode=0)
                        result = renderer._try_chrome(chrome_path, html_path, jpg_path, (800, 600))

                assert result == expected


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

    # Create a UTC timezone for testing
    tz_paris = pytz.timezone("Europe/Paris")

    with patch("pathlib.Path.write_text") as mock_write:
        with patch(
            "builtins.open",
            return_value=MagicMock(
                __enter__=MagicMock(
                    return_value=MagicMock(
                        read=MagicMock(return_value="<!-- FORECAST_DATA --><!-- GENERATED_AT -->")
                    )
                )
            ),
        ):
            with patch("pytz.timezone", return_value=tz_paris):
                renderer.render_html(data, output_path)
                written_content = mock_write.call_args[0][0]
                assert "Test Model" in written_content
                assert "2025-10-19 12:00" in written_content  # UTC time
                assert "UTC" in written_content


def test_pdf_generation(tmp_path):
    """Test PDF generation functionality."""
    renderer = ReportRenderer()
    html_path = tmp_path / "test.html"
    pdf_path = tmp_path / "test.pdf"
    html_path.write_text("<html><body>Test</body></html>")

    with patch("windforecast.render.ReportRenderer._find_chrome", return_value="/usr/bin/chrome"):
        with patch("subprocess.run") as mock_run:
            with patch("pathlib.Path.exists", return_value=True):
                result = renderer.generate_pdf(html_path, pdf_path)
                assert result is True
                mock_run.assert_called_once()
                cmd = mock_run.call_args[0][0]
                assert "--print-to-pdf" in " ".join(cmd)


def test_error_handling_image_generation(tmp_path):
    """Test error handling in image generation."""
    renderer = ReportRenderer()
    html_path = tmp_path / "test.html"
    jpg_path = tmp_path / "test.jpg"
    html_path.write_text("<html><body>Test</body></html>")

    # Test when no renderer is available
    with patch("windforecast.render.ReportRenderer._find_chrome", return_value=None):
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="No renderer available"):
                renderer.generate_jpg(html_path, jpg_path)

    # Test Chrome failure
    with patch("windforecast.render.ReportRenderer._find_chrome", return_value="/usr/bin/chrome"):
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
            with patch("shutil.which", return_value=None):  # No wkhtmltoimage fallback
                assert not renderer.generate_jpg(html_path, jpg_path)
