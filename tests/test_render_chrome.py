"""Test Chrome-specific render functionality."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from windforecast.render import ReportRenderer


def test_try_chrome_with_pillow(output_dir):
    """Test Chrome screenshot with Pillow conversion."""
    renderer = ReportRenderer()
    html_path = output_dir / "test.html"
    jpg_path = output_dir / "test.jpg"
    png_path = jpg_path.with_suffix(".png")

    # Create test HTML
    html_path.write_text("<html><body>Test</body></html>")

    # Mock subprocess.run and PIL.Image
    mock_image = MagicMock()
    mock_rgb = MagicMock()
    mock_image.convert.return_value = mock_rgb

    with patch("subprocess.run") as mock_run, patch(
        "windforecast.render.Image", MagicMock()
    ) as mock_pil, patch("windforecast.render.Image.open", return_value=mock_image), patch.object(
        Path, "unlink"
    ):

        # Make subprocess.run create a fake PNG file
        mock_run.return_value.returncode = 0
        png_path.write_text("")  # Create dummy file

        success = renderer._try_chrome("/fake/chrome", html_path, jpg_path, (800, 600))
        assert success
        mock_run.assert_called_once()
        mock_image.convert.assert_called_once_with("RGB")
        mock_rgb.save.assert_called_once()


def test_try_chrome_with_sips(output_dir):
    """Test Chrome screenshot with sips conversion on macOS."""
    renderer = ReportRenderer()
    html_path = output_dir / "test.html"
    jpg_path = output_dir / "test.jpg"

    # Create test HTML
    html_path.write_text("<html><body>Test</body></html>")

    png_path = jpg_path.with_suffix(".png")

    with patch("sys.platform", "darwin"), patch("windforecast.render.HAS_PILLOW", False), patch(
        "subprocess.run"
    ) as mock_run, patch.object(Path, "unlink"):

        # Make subprocess.run successful
        mock_run.return_value.returncode = 0

        # Create a fake PNG file that Chrome would create
        png_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.write_text("")

        success = renderer._try_chrome("/fake/chrome", html_path, jpg_path, (800, 600))
        assert success
        assert mock_run.call_count == 2  # One for Chrome, one for sips

        # Check the calls
        calls = mock_run.call_args_list
        assert "--screenshot=" in str(calls[0])  # Chrome screenshot call
        assert "sips" in str(calls[1])  # sips conversion call


def test_try_chrome_no_converter(output_dir):
    """Test Chrome screenshot without any available converter."""
    renderer = ReportRenderer()
    html_path = output_dir / "test.html"
    jpg_path = output_dir / "test.jpg"

    # Create test HTML
    html_path.write_text("<html><body>Test</body></html>")

    with patch("sys.platform", "linux"), patch.dict("sys.modules", {"PIL": None}), patch(
        "subprocess.run"
    ) as mock_run:

        success = renderer._try_chrome("/fake/chrome", html_path, jpg_path, (800, 600))
        assert not success
        mock_run.assert_called_once()


def test_try_chrome_subprocess_error(output_dir):
    """Test Chrome screenshot when subprocess.run raises an error."""
    renderer = ReportRenderer()
    html_path = output_dir / "test.html"
    jpg_path = output_dir / "test.jpg"

    # Create test HTML
    html_path.write_text("<html><body>Test</body></html>")

    # Mock subprocess.run to raise an error
    mock_error = Exception("Chrome error")
    with patch("subprocess.run", side_effect=mock_error):
        success = renderer._try_chrome("/fake/chrome", html_path, jpg_path, (800, 600))
        assert not success
