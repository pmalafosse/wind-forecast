"""Report generation and rendering utilities."""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .schemas import WindConfig

logger = logging.getLogger(__name__)

try:
    from PIL import Image

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    Image = None

logger = logging.getLogger(__name__)


class ReportRenderer:
    """HTML and image report renderer."""

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize renderer with optional custom template directory.

        Args:
            template_dir: Path to custom HTML templates. If None, uses built-in templates.
        """
        self.template_dir = template_dir or (Path(__file__).parent / "templates")

    def render_html(self, data: Dict[str, Any], output_path: Path) -> None:
        """
        Render forecast data to HTML report.

        Args:
            data: Processed forecast data dictionary with spots and forecasts
            output_path: Where to save the HTML file
        """
        with open(self.template_dir / "report.html") as f:
            template = f.read()

        # Convert data to HTML
        spot_tables = []
        for spot in data["spots"]:
            rows = []
            for r in spot["rows"]:
                rows.append(
                    f"""
                <tr class="{r['band']}">
                    <td>{r['time']}</td>
                    <td>{r['wind_kn']:.1f}</td>
                    <td>{r['gust_kn']:.1f}</td>
                    <td>{r['dir']} ({r['dir_deg']}°)</td>
                    <td>{r['precip_mm_h']:.1f}</td>
                    <td>{r['wave_m']:.1f if r['wave_m'] is not None else '-'}</td>
                    <td>{r['band']}</td>
                </tr>"""
                )

            spot_tables.append(
                f"""
            <section>
                <h2>{spot['spot']}</h2>
                <table>
                    <tr>
                        <th>Time</th>
                        <th>Wind (kn)</th>
                        <th>Gust (kn)</th>
                        <th>Direction</th>
                        <th>Rain (mm/h)</th>
                        <th>Wave (m)</th>
                        <th>Band</th>
                    </tr>
                    {''.join(rows)}
                </table>
            </section>"""
            )

        content = template.replace("<!-- FORECAST_DATA -->", "\n".join(spot_tables)).replace(
            "<!-- GENERATED_AT -->", data["generated_at"]
        )

        output_path.write_text(content)

    def generate_jpg(
        self, html_path: Path, jpg_path: Path, viewport: Tuple[int, int] = (2400, 1200)
    ) -> bool:
        """Generate JPG image from HTML report.

        Args:
            html_path: Path to HTML file
            jpg_path: Where to save the JPG
            viewport: Browser viewport dimensions

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Generating JPG from {html_path}")

        # Try Chrome/Chromium first
        if chrome_path := self._find_chrome():
            if self._try_chrome(chrome_path, html_path, jpg_path, viewport):
                return True

        # Try wkhtmltoimage
        if wk_path := shutil.which("wkhtmltoimage"):
            if self._try_wkhtmltoimage(wk_path, html_path, jpg_path):
                return True

        logger.error("No suitable renderer found")
        return False

    def _find_chrome(self) -> Optional[str]:
        """Find Chrome/Chromium executable.

        Returns:
            Path to Chrome/Chromium executable if found, None otherwise.
        """
        # Standard executable names
        chrome_names = ["google-chrome", "chrome", "chromium", "chromium-browser"]
        for name in chrome_names:
            if path := shutil.which(name):
                return path

        # macOS app bundle locations
        mac_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        if sys.platform == "darwin":
            for path in mac_paths:
                if Path(path).exists():
                    return path

        return None

    def _try_chrome(
        self, chrome_path: str, html_path: Path, jpg_path: Path, viewport: Tuple[int, int]
    ) -> bool:
        """Try generating image with Chrome/Chromium.

        Args:
            chrome_path: Path to Chrome/Chromium executable
            html_path: Path to source HTML file
            jpg_path: Path to output JPG file
            viewport: Browser viewport dimensions

        Returns:
            True if conversion successful, False otherwise
        """
        html_abs = html_path.absolute()
        jpg_abs = jpg_path.absolute()
        tmp_png = jpg_abs.with_suffix(".png")

        try:
            cmd = [
                chrome_path,
                "--headless",
                "--disable-gpu",
                f"--window-size={viewport[0]},{viewport[1]}",
                "--hide-scrollbars",
                "--screenshot=" + str(tmp_png),
                f"file://{html_abs}",
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            if HAS_PILLOW:
                img = Image.open(tmp_png)  # type: ignore
                rgb = img.convert("RGB")
                rgb.save(jpg_abs, "JPEG", quality=90)
                tmp_png.unlink()
                return True
            elif sys.platform == "darwin":
                subprocess.run(
                    ["sips", "-s", "format", "jpeg", str(tmp_png), "--out", str(jpg_abs)],
                    check=True,
                    capture_output=True,
                )
                tmp_png.unlink()
                return True

            return False

        except subprocess.CalledProcessError as e:
            logger.error(f"Chrome screenshot failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error generating JPG: {e}")
            return False

    def _try_wkhtmltoimage(self, wk_path: str, html_path: Path, jpg_path: Path) -> bool:
        """Try generating image with wkhtmltoimage.

        Args:
            wk_path: Path to wkhtmltoimage executable
            html_path: Path to source HTML file
            jpg_path: Path to output JPG file

        Returns:
            True if conversion successful, False otherwise
        """
        try:
            cmd = [wk_path, str(html_path), str(jpg_path)]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"wkhtmltoimage failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error generating JPG: {e}")
            return False
