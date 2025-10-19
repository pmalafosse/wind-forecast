"""Tests for image and PDF generation."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from windforecast.render import ReportRenderer


def test_viewport_calculation_with_multiple_days():
    """Test viewport calculation with multiple day sections."""
    html_content = """
    <div class="day-section">
        <h2>Day 1</h2>
        <div class="table-container">
            <table>
                <tr><th>Spot</th><th>09:00</th><th>10:00</th><th>11:00</th></tr>
                <tr><td>Spot1</td><td>Data1</td><td>Data2</td><td>Data3</td></tr>
                <tr><td>Spot2</td><td>Data4</td><td>Data5</td><td>Data6</td></tr>
            </table>
        </div>
    </div>
    <div class="day-section">
        <h2>Day 2</h2>
        <div class="table-container">
            <table>
                <tr><th>Spot</th><th>09:00</th><th>10:00</th></tr>
                <tr><td>Spot1</td><td>Data1</td><td>Data2</td></tr>
            </table>
        </div>
    </div>
    """
    renderer = ReportRenderer()
    width, height = renderer._calculate_viewport(html_content)

    # Verify dimensions
    assert width >= 800  # Minimum width
    assert height >= 600  # Minimum height
    assert width >= 60 + (4 * 100)  # Account for columns in first table
    assert height >= (5 * 40) + (2 * 100)  # Account for rows and section headers


def test_generate_jpg_no_renderer(tmp_path):
    """Test JPG generation when no renderer is available."""
    renderer = ReportRenderer()
    html_path = tmp_path / "test.html"
    jpg_path = tmp_path / "test.jpg"

    # Create test HTML file
    html_path.write_text("<html><body>Test</body></html>")

    with patch("windforecast.render.ReportRenderer._find_chrome", return_value=None):
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="No renderer available"):
                renderer.generate_jpg(html_path, jpg_path)


@pytest.mark.parametrize(
    "has_pillow,platform,expected_success",
    [
        (True, "linux", True),
        (False, "darwin", True),  # macOS should use sips fallback
        (False, "linux", False),  # Linux needs Pillow for PNG->JPG
    ],
)
def test_chrome_image_generation_platforms(has_pillow, platform, expected_success, tmp_path):
    """Test Chrome image generation across different platforms."""
    html_path = tmp_path / "test.html"
    jpg_path = tmp_path / "test.jpg"
    png_path = tmp_path / "test.png"  # PNG in the same directory
    html_path.write_text("<html><body>Test content</body></html>")

    renderer = ReportRenderer()
    chrome_path = "/usr/bin/chrome"
    viewport = (1024, 768)

    with patch("windforecast.render.HAS_PILLOW", has_pillow):
        with patch("sys.platform", platform):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                # Create a mock PNG file that Chrome would create
                png_path.touch()

                if has_pillow:
                    with patch("PIL.Image.open") as mock_open:
                        mock_img = MagicMock()
                        mock_open.return_value = mock_img
                        mock_img.convert.return_value = mock_img
                        result = renderer._try_chrome(chrome_path, html_path, jpg_path, viewport)
                else:
                    result = renderer._try_chrome(chrome_path, html_path, jpg_path, viewport)

                # Verify result
                assert result == expected_success

                # Verify Chrome command
                if result:
                    assert mock_run.call_count >= 1
                    chrome_cmd = mock_run.call_args_list[0][0][0]
                    assert "--headless=new" in chrome_cmd
                    assert f"--window-size={viewport[0]},{viewport[1]}" in chrome_cmd
                    assert "--screenshot=" + str(png_path) in chrome_cmd

                # Verify Chrome command
                chrome_call = mock_run.call_args_list[0]
                assert chrome_call[1]["check"] is True
                cmd = chrome_call[0][0]
                assert "--headless=new" in cmd
                assert f"--window-size={viewport[0]},{viewport[1]}" in cmd


def test_wkhtmltoimage_generation():
    """Test image generation using wkhtmltoimage."""
    renderer = ReportRenderer()
    html_path = Path("test.html")
    jpg_path = Path("test.jpg")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = renderer._try_wkhtmltoimage("wkhtmltoimage", html_path, jpg_path)
        assert result is True
        mock_run.assert_called_once_with(
            ["wkhtmltoimage", str(html_path), str(jpg_path)],
            check=True,
            capture_output=True,
        )


def test_chrome_finder_platforms():
    """Test Chrome executable finder on different platforms."""
    renderer = ReportRenderer()

    # Test Linux
    with patch("sys.platform", "linux"):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/chrome" if x == "google-chrome" else None
            path = renderer._find_chrome()
            assert path == "/usr/bin/chrome"

    # Test macOS with system Chrome
    mac_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    with patch("sys.platform", "darwin"):
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                path = renderer._find_chrome()
                assert path == mac_chrome
                mock_exists.assert_called_once()


def test_pdf_generation(tmp_path):
    """Test PDF generation functionality."""
    renderer = ReportRenderer()
    html_path = tmp_path / "test.html"
    pdf_path = tmp_path / "test.pdf"

    # Create test HTML file
    html_path.write_text("<html><body>Test content</body></html>")

    chrome_path = "/usr/bin/chrome"
    with patch("windforecast.render.ReportRenderer._find_chrome", return_value=chrome_path):
        with patch("subprocess.run") as mock_run:
            with patch("pathlib.Path.exists", return_value=True):
                result = renderer.generate_pdf(html_path, pdf_path)
                assert result is True

                # Verify Chrome command
                mock_run.assert_called_once()
                cmd = mock_run.call_args[0][0]
                assert chrome_path in cmd
                assert "--print-to-pdf=" + str(pdf_path.absolute()) in " ".join(cmd)
                assert str(html_path.absolute()) in " ".join(cmd)


def test_pdf_generation_failures():
    """Test PDF generation error handling."""
    renderer = ReportRenderer()
    html_path = Path("test.html")
    pdf_path = Path("test.pdf")

    # Test missing Chrome
    with patch("windforecast.render.ReportRenderer._find_chrome", return_value=None):
        result = renderer.generate_pdf(html_path, pdf_path)
        assert result is False

    # Test Chrome execution failure
    with patch("windforecast.render.ReportRenderer._find_chrome", return_value="/usr/bin/chrome"):
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
            with patch("pathlib.Path.exists", return_value=False):
                result = renderer.generate_pdf(html_path, pdf_path)
                assert result is False
