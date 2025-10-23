"""Report generation and rendering utilities.

AI Assistant Notice:
------------------
🚨 IMPORTANT: Before suggesting changes to this file, ALWAYS:
1. Check COPILOT.md for code patterns and conventions
2. Follow project structure in README.md
3. Review configuration guide in docs/configuration.md
4. Understand development workflow in CONTRIBUTING.md

Package Structure:
---------------
This file is part of the windforecast package:
src/windforecast/render.py

ALWAYS use package imports like:
    from windforecast.render import ReportRenderer
NEVER use direct file imports or reference files in root directory

This header ensures AI tools like GitHub Copilot maintain project consistency.
"""

import logging
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pytz

from .schemas import WindConfig

logger = logging.getLogger(__name__)

try:
    from PIL import Image

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    Image = None


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
        """Calculate star rating based on wind speed and config bands."""
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

    def _generate_daily_summary(
        self, data: Dict[str, Any], spots: List[str], all_forecasts: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """Generate a summary section with daily highlights."""
        days_data: Dict[date, Dict[str, List[Dict[str, Any]]]] = {}

        # Group forecasts by day and spot
        for time, spots_data in all_forecasts.items():
            dt = datetime.fromisoformat(time.replace("Z", "+00:00"))
            day = dt.date()

            if day not in days_data:
                days_data[day] = {}

            for spot, forecast in spots_data.items():
                if forecast["kiteable"]:
                    if spot not in days_data[day]:
                        days_data[day][spot] = []
                    days_data[day][spot].append(
                        {
                            "time": dt,
                            "wind_kn": forecast["wind_kn"],
                            "gust_kn": forecast["gust_kn"],
                            "stars": self._calculate_stars(
                                forecast["wind_kn"], WindConfig.model_validate(data["config"])
                            ),
                        }
                    )

        if not days_data:
            return None

        # Generate summary HTML
        sections = []
        for day, spots_data in sorted(days_data.items()):
            day_spots = []
            for spot, forecasts in spots_data.items():
                best_forecast = max(forecasts, key=lambda f: f["stars"])
                avg_wind = sum(f["wind_kn"] for f in forecasts) / len(forecasts)
                max_gust = max(f["gust_kn"] for f in forecasts)

                hours = sorted([f["time"].strftime("%H:%M") for f in forecasts])
                time_range = f"{hours[0]}-{hours[-1]}"

                spot_html = f"""<li>
                    <strong>{spot}</strong>: {len(forecasts)} kiteable hours ({time_range})
                    <div class="stats">
                        Avg wind: {avg_wind:.1f}kt, Max gust: {max_gust:.1f}kt
                        <div class="stars">{self._stars_html(best_forecast["stars"])}</div>
                    </div>
                </li>"""
                day_spots.append(spot_html)

            if day_spots:
                day_str = day.strftime("%A, %d %B")
                sections.append(
                    f"""<div class="day-summary">
                    <h3>{day_str}</h3>
                    <ul>{''.join(day_spots)}</ul>
                </div>"""
                )

        return f"""<div class="daily-summary">
            <h2>Daily Summary</h2>
            <div class="daily-grid">{''.join(sections)}</div>
        </div>"""

    def render_html(
        self, data: Dict[str, Any], output_path: Path, include_summary: bool = True
    ) -> None:
        """Render forecast data to HTML report."""
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
            spot_kiteable_count[spot["spot"]] = kiteable_count  # Include all spots

        # Initialize spot and hour tracking
        all_spots = {spot["spot"] for spot in data["spots"]}
        all_hours = {row["time"] for spot in data["spots"] for row in spot["rows"]}

        # Create data structures for different views
        kiteable_forecasts: Dict[str, Dict[str, Any]] = {}  # Only kiteable conditions
        all_forecasts_clean: Dict[str, Dict[str, Any]] = {}  # All conditions
        spot_tables: List[str] = []  # Initialize tables list
        kiteable_tables: List[str] = []  # Initialize kiteable conditions tables
        all_tables: List[str] = []  # Initialize all conditions tables

        # Track kiteable hours per day for each spot
        spot_kiteable_hours: Dict[date, Dict[str, Set[str]]] = {}  # {date: {spot: set(hours)}}
        kiteable_hours_by_day: Dict[date, Set[str]] = (
            {}
        )  # {date: set(hours)}        # Process forecasts and organize by views
        for hour in all_hours:
            dt = datetime.fromisoformat(hour.replace("Z", "+00:00"))
            day = dt.date()

            # Initialize data structures if needed
            if hour not in kiteable_forecasts:
                kiteable_forecasts[hour] = {}
                all_forecasts_clean[hour] = {}

            if day not in spot_kiteable_hours:
                spot_kiteable_hours[day] = {}
                kiteable_hours_by_day[day] = set()

            for spot in all_spots:
                if hour in all_forecasts and spot in all_forecasts[hour]:
                    forecast = all_forecasts[hour][spot]
                    # Add to all conditions view
                    all_forecasts_clean[hour][spot] = forecast

                    # Track kiteable conditions
                    if forecast["kiteable"]:
                        kiteable_forecasts[hour][spot] = forecast
                        # Initialize spot in tracking if needed
                        if spot not in spot_kiteable_hours[day]:
                            spot_kiteable_hours[day][spot] = set()
                        # Add hour to spot's kiteable hours for the day
                        spot_kiteable_hours[day][spot].add(hour)
                        kiteable_hours_by_day[day].add(hour)

        # Remove hours with no kiteable conditions from kiteable view
        kiteable_forecasts = {hour: spots for hour, spots in kiteable_forecasts.items() if spots}

        # Get all spots that have at least one kiteable condition
        kiteable_spots = {
            spot for day_data in spot_kiteable_hours.values() for spot in day_data.keys()
        }

        # Generate tables for each day and each view
        spot_tables.clear()
        kiteable_tables.clear()
        all_tables.clear()

        if not kiteable_spots:
            kiteable_tables.append("<p>No kiteable conditions found.</p>")

        # Function to generate daily table content
        def generate_table_section(
            day: date, forecast_data: Dict[str, Dict[str, Any]], view_type: str
        ) -> str:
            # Get hours for this day based on view type
            if view_type == "kiteable":
                # For kiteable view, only include hours with kiteable conditions
                day_hours = sorted(hour for hour in kiteable_hours_by_day[day])
            else:
                # For all-conditions view, include all hours for the day
                day_hours = sorted(
                    hour
                    for hour in all_hours
                    if datetime.fromisoformat(hour.replace("Z", "+00:00")).date() == day
                )

            if not day_hours:
                return ""

            # Get spots for this day based on view type
            if view_type == "kiteable":
                # For kiteable view, only include spots that have kiteable hours
                daily_spots = sorted(
                    [spot for spot in all_spots if spot in spot_kiteable_hours[day]],
                    key=lambda s: (len(spot_kiteable_hours[day].get(s, set())), s),
                    reverse=True,
                )
            else:
                # For all-conditions view, include all spots
                daily_spots = sorted(
                    all_spots,
                    key=lambda s: (len(spot_kiteable_hours[day].get(s, set())), s),
                    reverse=True,
                )

            rows = []

            # Generate header row
            header_cells = ["<th>Spot</th>"]
            for hour in day_hours:
                dt = datetime.fromisoformat(hour.replace("Z", "+00:00"))
                header_classes = ["hour-header"]
                # For kiteable view, all hours are kiteable. For all view, mark non-kiteable hours
                if view_type == "all" and hour not in kiteable_hours_by_day[day]:
                    header_classes.append("no-kiteable")
                header_cells.append(
                    f'<th data-hour="{hour}" class="{" ".join(header_classes)}">'
                    f'{dt.strftime("%H:%M")}</th>'
                )
            rows.append(f"<tr>{''.join(header_cells)}</tr>")

            # Generate data rows
            for spot in daily_spots:
                cells = [f"<td class='spotcol'><strong>{spot}</strong></td>"]
                spot_has_kiteable = False

                for hour in day_hours:
                    if hour in forecast_data and spot in forecast_data[hour]:
                        r = forecast_data[hour][spot]
                        config = WindConfig.model_validate(data["config"])
                        stars = self._calculate_stars(r["wind_kn"], config) if r["kiteable"] else 0
                        stars_html = (
                            f'<div class="stars">{self._stars_html(stars)}</div>'
                            if r["kiteable"]
                            else ""
                        )

                        # Determine wind band
                        wind_band = "below"
                        for band_name, threshold in config.conditions.bands:
                            if r["wind_kn"] >= threshold:
                                wind_band = band_name.lower().replace(" ", "-")
                                break

                        cell_classes = ["cell-data", wind_band]
                        style_attr = ""
                        if r["kiteable"]:
                            cell_classes.append("kiteable")
                            spot_has_kiteable = True
                        else:
                            cell_classes.append("not-kiteable")
                            # Only hide non-kiteable cells in the kiteable view
                            if view_type == "kiteable" and hour in kiteable_hours_by_day[day]:
                                style_attr = ' style="display: none;"'

                        # Get dir_deg from the field if present, otherwise 0
                        dir_deg = r.get("dir_deg", 0)  # Default to 0° (North) if not specified

                        cell_html = f"""<td class="{' '.join(cell_classes)}"{style_attr}>
                            <div class="dir">
                                <span class="dir-arrow" style="transform: rotate({dir_deg + 180}deg)">↑</span>
                                {r['dir']}
                            </div>
                            <div class="wind">
                                {r["wind_kn"]:.1f}/{r["gust_kn"]:.1f}kt
                            </div>
                            {stars_html}
                            {f'<div class="wave">🌊 {r["wave_m"]:.1f}m</div>' if r['wave_m'] is not None else ''}
                            {f'<div class="rain">🌧 {r["precip_mm_h"]:.1f}mm</div>' if r['precip_mm_h'] > 0 else ''}
                        </td>"""
                        cells.append(cell_html)
                    else:
                        cells.append('<td class="no-data">—</td>')

                # Add row with appropriate classes
                row_classes = ["spot-row"]
                # For all view, mark spots with no kiteable hours
                if view_type == "all" and not spot_has_kiteable:
                    row_classes.append("no-kiteable-spot")

                rows.append(f"<tr class='{' '.join(row_classes)}'>{''.join(cells)}</tr>")

            day_str = day.strftime("%A, %d %B")
            return f"""<div class="day-section">
                <h2>{day_str}</h2>
                <div class="table-container">
                    <table class="forecast-table">
                        {''.join(rows)}
                    </table>
                </div>
            </div>"""

        # Generate tables for each day and each view
        all_days = sorted(
            {datetime.fromisoformat(h.replace("Z", "+00:00")).date() for h in all_hours}
        )

        # Start with fresh lists
        spot_tables.clear()
        kiteable_tables.clear()
        all_tables.clear()

        # Add daily summary if enabled
        if include_summary:
            daily_summary = self._generate_daily_summary(data, list(all_spots), all_forecasts)
            if daily_summary:
                kiteable_tables.append(daily_summary)
                all_tables.append(daily_summary)

        # Handle case of no kiteable spots
        if not kiteable_spots:
            kiteable_tables.append("<p>No kiteable conditions found.</p>")

        # Generate tables for each day and view
        for day in all_days:
            # Generate tables for each view
            kiteable_section = generate_table_section(day, kiteable_forecasts, "kiteable")
            all_section = generate_table_section(day, all_forecasts_clean, "all")

            if kiteable_section:
                kiteable_tables.append(kiteable_section)
            if all_section:
                all_tables.append(all_section)

        # Create view divs
        spot_tables.append(
            f"""
            <div id="kiteable-view">
                {''.join(kiteable_tables)}
            </div>
            <div id="all-conditions-view">
                {''.join(all_tables)}
            </div>"""
        )

        # Add model updates section at the end of both views
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
            updates_section = f"""<div class="model-updates">
                <h3>Forecast Model Updates</h3>
                {''.join(model_info)}
            </div>"""
            spot_tables.append(updates_section)

        # Convert generated_at timestamp to CET
        generated_at = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
        cet = pytz.timezone("Europe/Paris")
        generated_at_cet = generated_at.astimezone(cet)

        content = template.replace("<!-- FORECAST_DATA -->", "\n".join(spot_tables)).replace(
            "<!-- GENERATED_AT -->", generated_at_cet.strftime("%Y-%m-%dT%H:%M:%S%z (CET)")
        )

        output_path.write_text(content)

    def _calculate_viewport(self, html_content: str) -> Tuple[int, int]:
        """Calculate optimal viewport size based on table content."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        max_columns = 0
        total_height = 0

        # Calculate dimensions from all day sections
        day_sections = soup.find_all("div", class_="day-section")
        for section in day_sections:
            table = section.find("table")
            if table:
                rows = table.find_all("tr")
                if rows:
                    # Count columns in first row (header)
                    columns = len(rows[0].find_all(["th", "td"]))
                    max_columns = max(max_columns, columns)
                    total_height += len(rows) * 40  # Approximate height per row

        # Calculate dimensions
        # Base width per column (minimum 100px)
        column_width = 100
        # First column is narrower (60px) and we add some padding
        width = 60 + (max_columns - 1) * column_width + 40  # +40px for padding
        # Add height for headers, padding, and other elements
        height = total_height + (
            len(day_sections) * 100
        )  # 100px extra per section for header and margins

        # Ensure minimum dimensions and reasonable maximum
        width = max(800, min(width, 7200))
        height = max(600, min(height, 4800))

        return (width, height)

    def generate_jpg(
        self, html_path: Path, jpg_path: Path, viewport: Optional[Tuple[int, int]] = None
    ) -> bool:
        """Generate JPG image from HTML report with dynamic resolution."""
        logger.info(f"Generating JPG from {html_path}")

        # Calculate viewport size from content if not provided
        if viewport is None:
            content = html_path.read_text()
            viewport = self._calculate_viewport(content)
            logger.info(f"Calculated viewport size: {viewport[0]}x{viewport[1]}")

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
        """Find Chrome/Chromium executable."""
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
        """Try generating image with Chrome/Chromium."""
        html_abs = html_path.absolute()
        jpg_abs = jpg_path.absolute()
        tmp_png = jpg_abs.with_suffix(".png")

        try:
            cmd = [
                chrome_path,
                "--headless=new",  # Use new headless mode
                "--disable-gpu",
                f"--window-size={viewport[0]},{viewport[1]}",
                "--hide-scrollbars",
                "--force-device-scale-factor=1.0",  # Full resolution
                "--screenshot=" + str(tmp_png),
                "--disable-features=TranslateUI",  # Disable UI elements that might affect rendering
                "--high-dpi-support=1",  # Enable high DPI support
                "--enable-high-resolution-time",  # Better timing for rendering
                "--full-page",  # Capture full page height
                "--no-margins",  # Remove any margins from the screenshot
                "--virtual-time-budget=1000",  # Allow time for full page rendering
                f"file://{html_abs}",
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            if HAS_PILLOW:
                img = Image.open(tmp_png)  # type: ignore
                rgb = img.convert("RGB")
                rgb.save(jpg_abs, "JPEG", quality=100, optimize=True, subsampling=0)
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
        """Try generating image with wkhtmltoimage."""
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
        """Generate PDF from HTML report with day-by-day tables."""
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
                "--no-sandbox",
                "--virtual-time-budget=5000",  # Give time for any JS to execute
                "--window-size=3000,2000",  # Viewport size for each page
                "--hide-scrollbars",
                "--run-all-compositor-stages-before-draw",
                "--disable-web-security",
                "--print-to-pdf-no-header",
                "--force-device-scale-factor=0.75",  # Adjust scale for readability
                "--print-to-pdf-orientation=landscape",
                f"--print-to-pdf={pdf_path.absolute()}",
                f"file://{html_path.absolute()}",
            ]

            # Run Chrome in headless mode to generate the PDF
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Check if the PDF was created
            if not pdf_path.exists():
                logger.error("PDF file was not created")
                return False

            logger.info("Successfully generated PDF with day-by-day tables")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Chrome PDF generation failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return False
