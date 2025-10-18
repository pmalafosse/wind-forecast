"""Test report rendering functionality."""

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from windforecast.render import ReportRenderer


def test_renderer_init():
    """Test ReportRenderer initialization."""
    renderer = ReportRenderer()
    assert renderer.template_dir.is_dir()

    # Test with custom template dir
    custom_dir = Path("/custom/templates")
    renderer = ReportRenderer(template_dir=custom_dir)
    assert renderer.template_dir == custom_dir


def test_calculate_stars():
    """Test star rating calculation based on wind speed."""
    renderer = ReportRenderer()
    assert renderer._calculate_stars(25) == 5
    assert renderer._calculate_stars(20) == 4
    assert renderer._calculate_stars(17) == 3
    assert renderer._calculate_stars(15) == 2
    assert renderer._calculate_stars(12) == 1
    assert renderer._calculate_stars(10) == 0


def test_stars_html():
    """Test HTML star rating generation."""
    renderer = ReportRenderer()
    assert renderer._stars_html(3) == "★★★"
    assert renderer._stars_html(0) == ""


def test_render_html(output_dir):
    """Test HTML report generation."""
    renderer = ReportRenderer()
    test_data = {
        "generated_at": "2024-03-14T12:00:00Z",
        "model_updates": {"arome_france_hd": {"title": "AROME HD", "run": "2024-03-14T12:00:00Z"}},
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

    output_path = output_dir / "test_report.html"
    renderer.render_html(test_data, output_path)

    assert output_path.exists()
    content = output_path.read_text()
    # Basic content checks
    assert "Test Spot" in content
    assert "WSW" in content
    assert "15.5" in content
    assert "★★" in content  # Should show 2 stars for 15.5 knots
    assert "🌊 1.2m" in content


def test_render_html_no_kiteable(output_dir):
    """Test HTML rendering with no kiteable conditions."""
    renderer = ReportRenderer()
    test_data = {
        "generated_at": "2024-03-14T12:00:00Z",
        "model_updates": {},
        "spots": [
            {
                "spot": "Test Spot",
                "rows": [
                    {
                        "time": "2024-03-14T12:00:00Z",
                        "wind_kn": 8.0,
                        "gust_kn": 10.0,
                        "dir_deg": 240.0,
                        "dir": "WSW",
                        "precip_mm_h": 0.0,
                        "wave_m": None,
                        "band": "light",
                        "kiteable": False,
                    }
                ],
            }
        ],
    }

    output_path = output_dir / "test_report.html"
    renderer.render_html(test_data, output_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "No kiteable conditions found" in content


def test_generate_jpg_no_renderer(output_dir, caplog):
    """Test JPG generation failure when no renderer is available."""
    renderer = ReportRenderer()
    html_path = output_dir / "test.html"
    jpg_path = output_dir / "test.jpg"

    # Create dummy HTML file
    html_path.write_text("<html><body>Test</body></html>")

    # Mock find_executable and _find_chrome to return None (no renderers available)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("shutil.which", lambda x: None)
        mp.setattr(renderer, "_find_chrome", lambda: None)
        with pytest.raises(RuntimeError, match="No renderer available for JPG generation"):
            renderer.generate_jpg(html_path, jpg_path)

        assert not jpg_path.exists()


def test_try_wkhtmltoimage(output_dir):
    """Test JPG generation with wkhtmltoimage."""
    renderer = ReportRenderer()
    html_path = output_dir / "test.html"
    jpg_path = output_dir / "test.jpg"

    # Create test HTML
    html_path.write_text("<html><body>Test</body></html>")

    # Mock successful run
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        success = renderer._try_wkhtmltoimage("/fake/wkhtmltoimage", html_path, jpg_path)
        assert success
        mock_run.assert_called_once_with(
            ["/fake/wkhtmltoimage", str(html_path), str(jpg_path)], check=True, capture_output=True
        )

    # Mock failed run
    with patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(1, [], stderr=b"test error")
    ):
        success = renderer._try_wkhtmltoimage("/fake/wkhtmltoimage", html_path, jpg_path)
        assert not success

    # Mock other error
    with patch("subprocess.run", side_effect=Exception("test error")):
        success = renderer._try_wkhtmltoimage("/fake/wkhtmltoimage", html_path, jpg_path)
        assert not success


def test_find_chrome():
    """Test Chrome executable detection."""
    renderer = ReportRenderer()

    # Test Unix-like systems with chrome in PATH
    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda x: (
            "/usr/bin/google-chrome" if x == "google-chrome" else None
        )
        chrome_path = renderer._find_chrome()
        assert chrome_path == "/usr/bin/google-chrome"

    # Test macOS with Chrome.app
    with patch("sys.platform", "darwin"), patch("shutil.which", return_value=None), patch(
        "windforecast.render.Path"
    ) as MockPath:

        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.__str__.return_value = (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        MockPath.return_value = mock_path_instance

        chrome_path = renderer._find_chrome()
        assert chrome_path == "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    # Test when no Chrome is found
    with patch("sys.platform", "darwin"), patch("shutil.which", return_value=None), patch(
        "windforecast.render.Path"
    ) as MockPath:

        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        MockPath.return_value = mock_path_instance

        chrome_path = renderer._find_chrome()
        assert chrome_path is None


def test_try_chrome_error(output_dir):
    """Test Chrome screenshot error handling."""
    renderer = ReportRenderer()
    html_path = output_dir / "test.html"
    jpg_path = output_dir / "test.jpg"

    # Create test HTML
    html_path.write_text("<html><body>Test</body></html>")

    # Mock subprocess to raise CalledProcessError
    mock_run = MagicMock(side_effect=subprocess.CalledProcessError(1, [], stderr=b"test error"))
    with patch("subprocess.run", mock_run):
        success = renderer._try_chrome("/fake/chrome", html_path, jpg_path, (800, 600))
        assert not success
        assert not jpg_path.exists()
