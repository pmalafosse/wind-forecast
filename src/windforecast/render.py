"""Report generation and rendering utilities."""

import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytz

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

    def __init__(self, config: Optional[WindConfig] = None, template_dir: Optional[Path] = None):
        """Initialize renderer with optional config and custom template directory.

        Args:
            config: WindConfig object containing wind band thresholds
            template_dir: Path to custom HTML templates. If None, uses built-in templates.
        """
        self.config = config
        self.template_dir = template_dir or (Path(__file__).parent / "templates")

    def _calculate_stars(self, wind_kn: float, config: WindConfig) -> int:
        """Calculate star rating based on wind speed and config bands.

        The star rating scale is:
        - 6 stars: Insane (expert-only conditions)
        - 5 stars: Great (perfect conditions)
        - 4 stars: Very good conditions
        - 3 stars: Good/Hardcore (challenging conditions)
        - 2 stars: OK conditions
        - 1 star:  Light conditions
        - 0 stars: Too light or too strong

        Args:
            wind_kn: Wind speed in knots
            config: Configuration object containing wind bands

        Returns:
            Integer from 0 to 6 representing the star rating
        """
        bands = config.conditions.bands

        # Skip "too much" (dangerous conditions)
        if wind_kn >= bands[0][1]:  # Above "too much" threshold
            return 0

        star_mapping = {
            "hardcore": 3,  # Challenging conditions
            "insane": 6,  # Expert conditions (highest rating)
            "great": 5,  # Perfect conditions
            "very good": 4,  # Very good conditions
            "good": 3,  # Good conditions
            "ok": 2,  # Acceptable conditions
            "light": 1,  # Light wind conditions
            "below": 0,  # Too light
        }

        # Find the appropriate band
        for band_name, threshold in bands:
            if wind_kn >= threshold:
                return star_mapping.get(band_name, 0)
        return 0

    @staticmethod
    def _stars_html(count: int) -> str:
        """Generate HTML for star rating."""
        return "★" * count

    def render_html(
        self, data: Dict[str, Any], output_path: Path, include_summary: bool = False
    ) -> None:
        """Render forecast data to HTML report.

        Args:
            data: Processed forecast data dictionary with spots and forecasts
            output_path: Where to save the HTML file
            include_summary: Whether to include the daily summary section
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

        # Calculate daily summaries
        daily_stats: Dict[Any, Dict[str, Any]] = {}
        config = WindConfig.model_validate(data["config"])

        for hour in sorted_hours:
            dt = datetime.fromisoformat(hour.replace("Z", "+00:00"))
            day = dt.date()
            day_str = dt.strftime("%A, %d/%m")

            if day not in daily_stats:
                daily_stats[day] = {
                    "day_str": day_str,
                    "spots": {},
                }

            for spot in sorted_spots:
                if spot not in daily_stats[day]["spots"]:
                    daily_stats[day]["spots"][spot] = {
                        "kiteable_hours": 0,
                        "total_stars": 0,
                        "total_wind": 0,
                        "total_gusts": 0,
                        "total_waves": 0,
                        "wave_count": 0,
                    }

                if hour in all_forecasts and spot in all_forecasts[hour]:
                    r = all_forecasts[hour][spot]
                    if r["kiteable"]:
                        stats = daily_stats[day]["spots"][spot]
                        stats["kiteable_hours"] += 1
                        stats["total_stars"] += self._calculate_stars(r["wind_kn"], config)
                        stats["total_wind"] += r["wind_kn"]
                        stats["total_gusts"] += r["gust_kn"]
                        if r["wave_m"] is not None:
                            stats["total_waves"] += r["wave_m"]
                            stats["wave_count"] += 1

        # Generate daily summary HTML
        daily_parts = [
            '<div class="daily-summary"><h2>Daily Summary</h2><div class="daily-grid">'
        ]  # type: List[str]

        for day in sorted(daily_stats.keys()):
            day_data = daily_stats[day]
            day_spots = []

            # Calculate spot rankings for this day
            for spot, stats in day_data["spots"].items():
                if stats["kiteable_hours"] > 0:
                    avg_stars = stats["total_stars"] / stats["kiteable_hours"]
                    avg_wind = stats["total_wind"] / stats["kiteable_hours"]
                    avg_gusts = stats["total_gusts"] / stats["kiteable_hours"]
                    avg_waves = (
                        stats["total_waves"] / stats["wave_count"]
                        if stats["wave_count"] > 0
                        else None
                    )

                    day_spots.append(
                        {
                            "spot": spot,
                            "hours": stats["kiteable_hours"],
                            "avg_stars": avg_stars,
                            "avg_wind": avg_wind,
                            "avg_gusts": avg_gusts,
                            "avg_waves": avg_waves,
                        }
                    )

            # Sort spots by kiteable hours then average stars
            day_spots.sort(key=lambda x: (x["hours"], x["avg_stars"]), reverse=True)

            if day_spots:
                daily_parts.append(f'<div class="day-summary">')
                daily_parts.append(f'<h3>{day_data["day_str"]}</h3><ul>')
                for spot_data in day_spots:
                    wave_info = (
                        f", Waves: {spot_data['avg_waves']:.1f}m"
                        if spot_data["avg_waves"] is not None
                        else ""
                    )
                    daily_parts.append(
                        f'<li><strong>{spot_data["spot"]}</strong> ({spot_data["hours"]} hours)'
                        f'<div class="stats">'
                        f'<div class="stars">{self._stars_html(round(spot_data["avg_stars"]))}</div> | '
                        f'Wind: {spot_data["avg_wind"]:.1f}/{spot_data["avg_gusts"]:.1f}kt{wave_info}'
                        f"</div></li>"
                    )
                daily_parts.append("</ul></div>")

        daily_parts.extend(["</div></div>"])

        if not sorted_spots:
            spot_tables = ["<p>No kiteable conditions found.</p>"]
        else:
            # Build table rows
            rows = []

            # Header row
            header_cells = ["<th>Spot (kiteable hours)</th>"]
            prev_day = None
            for hour in sorted_hours:
                # Handle 'Z' timezone designator for Python 3.8
                dt = datetime.fromisoformat(hour.replace("Z", "+00:00"))
                curr_day = dt.date()

                # Add day separator class if day changes
                day_class = ' class="day-start"' if prev_day != curr_day else ""
                header_cells.append(
                    f'<th{day_class}>{dt.strftime("%a %d/%m")}<br>{dt.strftime("%H:%M")}</th>'
                )
                prev_day = curr_day
            rows.append(f"<tr>{''.join(header_cells)}</tr>")

            # Data rows
            for spot in sorted_spots:
                cells = [
                    f"<td class='spotcol'><strong>{spot}</strong> ({spot_kiteable_count[spot]})</td>"
                ]
                prev_day = None
                for hour in sorted_hours:
                    dt = datetime.fromisoformat(hour.replace("Z", "+00:00"))
                    curr_day = dt.date()
                    day_class = " day-start" if prev_day != curr_day else ""
                    prev_day = curr_day

                    if hour in all_forecasts and spot in all_forecasts[hour]:
                        r = all_forecasts[hour][spot]
                        # Convert dict config back to WindConfig for _calculate_stars
                        config = WindConfig.model_validate(data["config"])
                        stars = self._calculate_stars(r["wind_kn"], config) if r["kiteable"] else 0
                        stars_html = (
                            f'<div class="stars">{self._stars_html(stars)}</div>'
                            if r["kiteable"]
                            else ""
                        )
                        cells.append(
                            f"""
                            <td class="{'kiteable' if r['kiteable'] else 'not-kiteable'}{day_class}">
                                <div class="wind">{r['wind_kn']:.1f}/{r['gust_kn']:.1f}kt</div>
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

        # Only include daily summary if requested
        report_parts = daily_parts + spot_tables if include_summary else spot_tables

        # Convert generated_at timestamp to CET
        generated_at = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
        cet = pytz.timezone("Europe/Paris")
        generated_at_cet = generated_at.astimezone(cet)

        content = template.replace("<!-- FORECAST_DATA -->", "\n".join(report_parts)).replace(
            "<!-- GENERATED_AT -->", generated_at_cet.strftime("%Y-%m-%dT%H:%M:%S%z (CET)")
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

        # Check if any renderer is available
        chrome_path = self._find_chrome()
        wk_path = shutil.which("wkhtmltoimage")

        if not chrome_path and not wk_path:
            logger.error("Could not find a renderer (Chrome/Chromium or wkhtmltoimage)")
            raise RuntimeError("No renderer available for JPG generation")

        # Try Chrome/Chromium first
        if chrome_path and self._try_chrome(chrome_path, html_path, jpg_path, viewport):
            return True

        # Try wkhtmltoimage
        if wk_path and self._try_wkhtmltoimage(wk_path, html_path, jpg_path):
            return True

        logger.error("Rendering attempts failed")
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

    def generate_pdf(self, html_path: Path, pdf_path: Path) -> bool:
        """Generate PDF from HTML report.

        Args:
            html_path: Path to HTML file
            pdf_path: Where to save the PDF

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Generating PDF from {html_path}")

        # Check if Chrome is available
        chrome_path = self._find_chrome()
        if not chrome_path:
            logger.error("Could not find Chrome/Chromium for PDF generation")
            return False

        try:
            cmd = [
                chrome_path,
                "--headless",
                "--disable-gpu",
                "--print-to-pdf=" + str(pdf_path.absolute()),
                f"file://{html_path.absolute()}",
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Chrome PDF generation failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return False
