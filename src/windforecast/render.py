"""Report generation and rendering utilities."""

import logging
import shutil
import subprocess
import sys
from datetime import datetime
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

    @staticmethod
    def _calculate_stars(wind_kn: float) -> int:
        """Calculate star rating based on wind speed."""
        if wind_kn >= 25:
            return 5
        elif wind_kn >= 20:
            return 4
        elif wind_kn >= 17:
            return 3
        elif wind_kn >= 15:
            return 2
        elif wind_kn >= 12:
            return 1
        return 0

    @staticmethod
    def _stars_html(count: int) -> str:
        """Generate HTML for star rating."""
        return "★" * count

    def render_html(self, data: Dict[str, Any], output_path: Path) -> None:
        """
        Render forecast data to HTML report.

        Args:
            data: Processed forecast data dictionary with spots and forecasts
            output_path: Where to save the HTML file
        """
        with open(self.template_dir / "report.html") as f:
            template = f.read()

        # Collect all forecast data and count kiteable hours per spot
        all_forecasts: Dict[str, Dict[str, Any]] = {}
        spot_kiteable_count: Dict[str, int] = {}

        for spot in data["spots"]:
            kiteable_count = 0
            for r in spot["rows"]:
                time = r["time"]
                if time not in all_forecasts:
                    all_forecasts[time] = {}
                all_forecasts[time][spot["spot"]] = r
                if r["kiteable"]:
                    kiteable_count += 1
            if kiteable_count > 0:  # Only include spots that have kiteable conditions
                spot_kiteable_count[spot["spot"]] = kiteable_count

        # Find times with at least one kiteable condition
        kiteable_hours = {
            time
            for time, spots in all_forecasts.items()
            if any(r["kiteable"] for r in spots.values())
        }

        # Sort hours chronologically and spots by kiteable hours
        sorted_hours = sorted(kiteable_hours)
        sorted_spots = sorted(
            spot_kiteable_count.keys(), key=lambda s: spot_kiteable_count[s], reverse=True
        )

        if not sorted_spots:
            spot_tables = ["<p>No kiteable conditions found.</p>"]
        else:
            # Build table rows
            rows = []

            # Header row
            header_cells = ["<th>Spot (kiteable hours)</th>"]
            for hour in sorted_hours:
                dt = datetime.fromisoformat(hour)
                header_cells.append(f"<th>{dt.strftime('%d/%m %H:%M')}</th>")
            rows.append(f"<tr>{''.join(header_cells)}</tr>")

            # Data rows
            for spot in sorted_spots:
                cells = [
                    f"<td class='spotcol'><strong>{spot}</strong> ({spot_kiteable_count[spot]})</td>"
                ]
                for hour in sorted_hours:
                    if hour in all_forecasts and spot in all_forecasts[hour]:
                        r = all_forecasts[hour][spot]
                        stars = self._calculate_stars(r["wind_kn"]) if r["kiteable"] else 0
                        stars_html = (
                            f'<div class="stars">{self._stars_html(stars)}</div>'
                            if r["kiteable"]
                            else ""
                        )
                        cells.append(
                            f"""
                            <td class="{'kiteable' if r['kiteable'] else 'not-kiteable'}">
                                <div class="wind">{r['wind_kn']:.0f}/{r['gust_kn']:.0f}kt</div>
                                <div class="dir">{r['dir']}</div>
                                {stars_html}
                                {f'<div class="wave">🌊 {r["wave_m"]:.1f}m</div>' if r['wave_m'] is not None else ''}
                                {f'<div class="rain">🌧 {r["precip_mm_h"]:.1f}mm</div>' if r['precip_mm_h'] > 0 else ''}
                            </td>"""
                        )
                    else:
                        cells.append('<td class="no">—</td>')
                rows.append(f"<tr>{''.join(cells)}</tr>")

            spot_tables = [
                f"""
                <div class="table-container">
                    <table class="forecast-table">
                        {''.join(rows)}
                    </table>
                </div>"""
            ]

        # Add model updates section
        model_info = []
        for model_id, info in data.get("model_updates", {}).items():
            if info.get("run"):
                run_time = datetime.fromisoformat(info["run"].replace("Z", "+00:00"))
                model_info.append(
                    f"""<div class="model-info">
                        <span class="model-name">{info['title']}</span>
                        <span class="model-run">Run: {run_time.strftime('%Y-%m-%d %H:%M')} UTC</span>
                    </div>"""
                )

        if model_info:
            spot_tables.append(
                f"""
                <div class="model-updates">
                    <h3>Forecast Model Updates</h3>
                    {''.join(model_info)}
                </div>"""
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
