"""Report generation and rendering utilities."""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pytz

from .schemas import WindConfig

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

    def render_html(self, data: Dict[str, Any], output_path: Path) -> None:
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
        min15_hours = {
            row["time"]
            for spot in data["spots"]
            for row in spot["rows"]
            if row.get("freq") == "15min"
        }

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
                is_min15 = hour in min15_hours
                dot = (
                    ' <span class="min15-dot" title="15-min AROME (higher resolution)">·</span>'
                    if is_min15
                    else ""
                )
                header_cells.append(
                    f'<th data-hour="{hour}" class="{" ".join(header_classes)}">'
                    f'{dt.strftime("%H:%M")}{dot}</th>'
                )
            rows.append(f"<tr>{''.join(header_cells)}</tr>")

            is_today = day == date.today()

            # Generate data rows
            for spot in daily_spots:
                spot_slug = spot.lower().replace(" ", "_")
                if is_today:
                    spot_cell = (
                        f"<td class='spotcol'><strong>"
                        f"<a class='spot-link' href='#' "
                        f"onclick=\"showPlot('{spot_slug}'); return false;\">{spot}</a>"
                        f"</strong></td>"
                    )
                else:
                    spot_cell = f"<td class='spotcol'><strong>{spot}</strong></td>"
                cells = [spot_cell]
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
            today_attr = ' data-today="true"' if day == date.today() else ""
            return f"""<div class="day-section"{today_attr}>
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

        # Generate daily summary
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

        # Build model updates for the info popup
        model_rows = []
        for model_id, info in data.get("model_updates", {}).items():
            if info.get("run"):
                run_time = datetime.fromisoformat(info["run"].replace("Z", "+00:00"))
                model_rows.append(
                    f'<div class="info-model-row">'
                    f'<span class="info-model-name">{info["title"]}</span>'
                    f'<span class="info-model-run">{run_time.strftime("%Y-%m-%d %H:%M")} UTC</span>'
                    f"</div>"
                )
        model_updates_html = "".join(model_rows)

        # Convert generated_at timestamp to CET
        generated_at = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
        cet = pytz.timezone("Europe/Paris")
        generated_at_cet = generated_at.astimezone(cet)

        content = (
            template.replace("<!-- FORECAST_DATA -->", "\n".join(spot_tables))
            .replace(
                "<!-- GENERATED_AT -->", generated_at_cet.strftime("%Y-%m-%dT%H:%M:%S%z (CET)")
            )
            .replace("<!-- MODEL_UPDATES -->", model_updates_html)
        )

        output_path.write_text(content)
