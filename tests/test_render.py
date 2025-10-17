"""Test report rendering functionality."""

from pathlib import Path

import pytest

from windforecast.render import ReportRenderer


def test_renderer_init():
    """Test ReportRenderer initialization."""
    renderer = ReportRenderer()
    assert renderer.template_dir.is_dir()


def test_render_html(output_dir):
    """Test HTML report generation."""
    renderer = ReportRenderer()
    test_data = {
        "generated_at": "2024-03-14T12:00:00Z",
        "model_updates": {"arome_france_hd": {"run": "2024-03-14T12:00:00Z"}},
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


def test_generate_jpg_no_renderer(output_dir, caplog):
    """Test JPG generation failure when no renderer is available."""
    renderer = ReportRenderer()
    html_path = output_dir / "test.html"
    jpg_path = output_dir / "test.jpg"

    # Create dummy HTML file
    html_path.write_text("<html><body>Test</body></html>")

    # Mock find_executable to return None (no renderers available)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("shutil.which", lambda x: None)
        success = renderer.generate_jpg(html_path, jpg_path)

        assert not success
        assert not jpg_path.exists()
        assert "No suitable renderer found" in caplog.text
