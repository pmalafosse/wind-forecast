"""Forecast data fetching and processing."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

from .schemas import WindConfig, WindSpot

logger = logging.getLogger(__name__)


class ForecastClient:
    """Client for fetching and processing wind forecast data."""

    def __init__(self, config: WindConfig):
        self.config = config
        self.base_url = "https://api.open-meteo.com/v1/meteofrance"
        self.marine_url = "https://marine-api.open-meteo.com/v1/marine"

    def fetch_forecasts(self) -> Dict[str, Any]:
        """
        Fetch forecast data for all configured spots.

        Returns:
            Dictionary containing processed forecast data.
        """
        logger.info("Fetching forecast data...")
        spots = self.config.spots
        hourly, min15, waves = self._fetch_weather(spots)
        model_updates = self._fetch_model_updates()

        return self._process_forecasts(hourly, min15, waves, model_updates)

    def _fetch_weather(
        self, spots: List[WindSpot]
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Fetch weather data from API endpoints."""
        lats = ",".join(str(s.lat) for s in spots)
        lons = ",".join(str(s.lon) for s in spots)

        # Hourly forecast
        params_hourly = {
            "latitude": lats,
            "longitude": lons,
            "models": self.config.forecast.model,
            "hourly": self.config.forecast.hourly_vars,
            "wind_speed_unit": "kn",
            "timezone": "Europe/Madrid",
            "forecast_hours": self.config.forecast.forecast_hours_hourly,
        }
        r_hourly = requests.get(self.base_url, params=params_hourly, timeout=30)
        r_hourly.raise_for_status()

        # 15-minute forecast
        params_min15 = {
            "latitude": lats,
            "longitude": lons,
            "models": self.config.forecast.model,
            "minutely_15": self.config.forecast.hourly_vars,  # Use same vars
            "wind_speed_unit": "kn",
            "timezone": "Europe/Madrid",
            "forecast_minutely_15": self.config.forecast.forecast_min15,
        }
        r_min15 = requests.get(self.base_url, params=params_min15, timeout=30)
        r_min15.raise_for_status()

        # Marine (waves)
        params_wave = {
            "latitude": lats,
            "longitude": lons,
            "hourly": self.config.forecast.wave_vars,
            "timezone": "Europe/Madrid",
            "forecast_hours": self.config.forecast.forecast_hours_hourly,
            "cell_selection": "sea",
        }
        r_wave = requests.get(self.marine_url, params=params_wave, timeout=30)
        r_wave.raise_for_status()

        return r_hourly.json(), r_min15.json(), r_wave.json()

    def _fetch_model_updates(self) -> Dict[str, Any]:
        """Fetch model update metadata."""
        base = "https://openmeteo.s3.amazonaws.com/data_spatial"
        models = {
            "meteofrance_arome_france_hd": "AROME France HD (hourly)",
            "meteofrance_arome_france_hd_15min": "AROME France HD (15-min)",
        }
        out = {}
        for m, title in models.items():
            url = f"{base}/{m}/latest.json"
            try:
                r = requests.get(url, timeout=20)
                r.raise_for_status()
                j = r.json()
                run_iso = j.get("reference_time")
                last_modified_time = j.get("last_modified_time")
                out[m] = {
                    "title": title,
                    "run": run_iso,
                    "last_modified_time": last_modified_time,
                    "source": url,
                }
            except Exception as e:
                out[m] = {"title": title, "run": None, "source": url, "error": str(e)}
        return out

    def _process_forecasts(
        self,
        hourly: Dict[str, Any],
        min15: Dict[str, Any],
        waves: Dict[str, Any],
        model_updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process raw forecast data into final format."""

        def _classify_band(kn: float) -> str:
            """Classify wind speed into bands."""
            for label, thr in self.config.conditions.bands:
                if kn >= thr:
                    return label
            return "below"

        def _direction_in_sector(deg: float, sector: Optional[Dict[str, Any]]) -> bool:
            """Check if wind direction is within sector."""
            if sector is None:
                return True
            start = float(str(sector.get("start", 0)))
            end = float(str(sector.get("end", 360)))
            wrap = sector.get("wrap", False)
            if not wrap:
                return start <= deg <= end
            # wrapped: e.g., 225..360 and 0..45
            return (deg >= start) or (deg <= end)

        def _build_df(
            spot_name: str,
            spot_meta: Dict[str, Any],
            h: Dict[str, Any],
            m15: Dict[str, Any],
            wav: Dict[str, Any],
        ) -> pd.DataFrame:
            """Build DataFrame for a spot."""
            # Hourly data
            ht = h["hourly"]["time"]
            dfh = pd.DataFrame(
                {
                    "time": pd.to_datetime(ht),
                    "wind_kn": h["hourly"]["wind_speed_10m"],
                    "gust_kn": h["hourly"]["wind_gusts_10m"],
                    "dir_deg": h["hourly"]["wind_direction_10m"],
                    "precip": h["hourly"]["precipitation"],
                    "freq": "H",
                }
            )

            # 15-min data
            mt = m15.get("minutely_15", {}).get("time", [])
            if mt:
                dfm = pd.DataFrame(
                    {
                        "time": pd.to_datetime(mt),
                        "wind_kn": m15["minutely_15"]["wind_speed_10m"],
                        "gust_kn": m15["minutely_15"]["wind_gusts_10m"],
                        "dir_deg": m15["minutely_15"]["wind_direction_10m"],
                        "precip": m15["minutely_15"]["precipitation"],
                        "freq": "15min",
                    }
                )
            else:
                dfm = pd.DataFrame(columns=dfh.columns)

            # Wave data
            wt = wav["hourly"]["time"]
            dfw = pd.DataFrame({"time": pd.to_datetime(wt), "wave_m": wav["hourly"]["wave_height"]})

            # Prefer 15-min where available
            df = pd.concat(
                [dfm, dfh[dfh["time"] > dfm["time"].max()] if not dfm.empty else dfh],
                ignore_index=True,
            )

            # Merge waves
            df = df.merge(dfw, on="time", how="left")

            # Daytime filter
            df["local_hour"] = df["time"].dt.hour
            df = df[
                (df["local_hour"] >= self.config.time_window.day_start)
                & (df["local_hour"] <= self.config.time_window.day_end)
            ].copy()

            # Analyze conditions
            df.dropna(inplace=True)
            df["dir_ok"] = df["dir_deg"].apply(
                lambda d: _direction_in_sector(d, spot_meta.get("dir_sector"))
            )
            df["rain_ok"] = df["precip"] <= self.config.conditions.rain_limit
            df["speed_ok"] = df["wind_kn"] >= 12.0
            df["valid"] = df["dir_ok"] & df["rain_ok"] & df["speed_ok"]
            df["band"] = df["wind_kn"].apply(_classify_band)
            df["kiteable"] = df["valid"]
            df["spot"] = spot_name

            return df[
                [
                    "spot",
                    "time",
                    "wind_kn",
                    "gust_kn",
                    "dir_deg",
                    "precip",
                    "wave_m",
                    "band",
                    "kiteable",
                ]
            ].sort_values("time")

        # Process all spots
        Lh = [hourly] if isinstance(hourly, dict) else hourly
        Lm15 = [min15] if isinstance(min15, dict) else min15
        Lw = [waves] if isinstance(waves, dict) else waves

        result = []
        for i, spot in enumerate(self.config.spots):
            df = _build_df(spot.name, spot.dict(), Lh[i], Lm15[i], Lw[i])
            rows = []
            for _, r in df.iterrows():
                rows.append(
                    {
                        "time": r["time"].isoformat(),
                        "wind_kn": float(r["wind_kn"]),
                        "gust_kn": float(r["gust_kn"]),
                        "dir_deg": float(r["dir_deg"]),
                        "dir": self._deg_to_16pt(r["dir_deg"]),
                        "precip_mm_h": float(r["precip"]),
                        "wave_m": None if pd.isna(r["wave_m"]) else float(r["wave_m"]),
                        "band": r["band"],
                        "kiteable": bool(r["kiteable"]),
                    }
                )
            result.append({"spot": spot.name, "rows": rows})

        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "model_updates": model_updates,
            "spots": result,
        }

    @staticmethod
    def _deg_to_16pt(d: float) -> str:
        """Convert degrees to 16-point compass direction."""
        labels = [
            "N",
            "NNE",
            "NE",
            "ENE",
            "E",
            "ESE",
            "SE",
            "SSE",
            "S",
            "SSW",
            "SW",
            "WSW",
            "W",
            "WNW",
            "NW",
            "NNW",
        ]
        idx = int((d + 11.25) // 22.5) % 16
        return labels[idx]
