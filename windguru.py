# kite_windows_json_only.py
import json, math, os
from datetime import datetime
import itertools
from pathlib import Path
import requests
import pandas as pd

def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)

# Load configuration
CONFIG = load_config()
SPOTS = CONFIG["spots"]
ONLY_AROME_MODELS = CONFIG["forecast"]["model"]
HOURLY_VARS = CONFIG["forecast"]["hourly_vars"]
MIN15_VARS = HOURLY_VARS
WAVE_VARS = CONFIG["forecast"]["wave_vars"]

FORECAST_HOURS_HOURLY = CONFIG["forecast"]["forecast_hours_hourly"]
FORECAST_MIN15 = CONFIG["forecast"]["forecast_min15"]

DAY_START = CONFIG["time_window"]["day_start"]
DAY_END = CONFIG["time_window"]["day_end"]

BANDS = CONFIG["conditions"]["bands"]
RAIN_LIMIT = CONFIG["conditions"]["rain_limit"]
MIN_RUN_HOURS = CONFIG["conditions"]["min_run_hours"]

# ---------- 3) Helpers ----------
def deg_to_16pt(d):
    labels = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
              "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    idx = int((d + 11.25) // 22.5) % 16
    return labels[idx]

def direction_in_sector(deg, sector):
    if sector is None:
        return True
    start, end, wrap = sector["start"], sector["end"], sector.get("wrap", False)
    if not wrap:
        return start <= deg <= end
    # wrapped: e.g., 225..360 and 0..45
    return (deg >= start) or (deg <= end)

def classify_band(kn):
    for label, thr in BANDS:
        if kn >= thr:
            return label
    return "below"

# ---------- 4) Fetch ----------
def fetch_weather(spots):
    lats = ",".join(str(s["lat"]) for s in spots)
    lons = ",".join(str(s["lon"]) for s in spots)

    base = "https://api.open-meteo.com/v1/meteofrance"
    params_hourly = {
        "latitude": lats, "longitude": lons,
        "models": ONLY_AROME_MODELS,
        "hourly": HOURLY_VARS,
        "wind_speed_unit": "kn",
        "timezone": "Europe/Madrid",
        "forecast_hours": FORECAST_HOURS_HOURLY,
    }
    params_min15 = {
        "latitude": lats, "longitude": lons,
        "models": ONLY_AROME_MODELS,
        "minutely_15": MIN15_VARS,
        "wind_speed_unit": "kn",
        "timezone": "Europe/Madrid",
        "forecast_minutely_15": FORECAST_MIN15,
    }
    r_hourly = requests.get(base, params=params_hourly, timeout=30)
    r_hourly.raise_for_status()
    r_min15  = requests.get(base, params=params_min15,  timeout=30)
    r_min15.raise_for_status()

    # Marine (waves)
    base_marine = "https://marine-api.open-meteo.com/v1/marine"
    params_wave = {
        "latitude": lats, "longitude": lons,
        "hourly": WAVE_VARS,
        "timezone": "Europe/Madrid",
        "forecast_hours": FORECAST_HOURS_HOURLY,
        "cell_selection": "sea"
    }
    r_wave = requests.get(base_marine, params=params_wave, timeout=30)
    r_wave.raise_for_status()

    return r_hourly.json(), r_min15.json(), r_wave.json()

def as_locations(payload):
    return payload if isinstance(payload, list) else [payload]

# ---------- 5) Per-spot processing ----------
def build_df(name, spot_meta, h, m15, wav):
    # Hourly
    ht = h["hourly"]["time"]
    dfh = pd.DataFrame({
        "time": pd.to_datetime(ht),
        "wind_kn": h["hourly"]["wind_speed_10m"],
        "gust_kn": h["hourly"]["wind_gusts_10m"],
        "dir_deg": h["hourly"]["wind_direction_10m"],
        "precip":  h["hourly"]["precipitation"],
        "freq":    "H"
    })

    # 15-min
    mt = m15.get("minutely_15", {}).get("time", [])
    if mt:
        dfm = pd.DataFrame({
            "time": pd.to_datetime(mt),
            "wind_kn": m15["minutely_15"]["wind_speed_10m"],
            "gust_kn": m15["minutely_15"]["wind_gusts_10m"],
            "dir_deg": m15["minutely_15"]["wind_direction_10m"],
            "precip":  m15["minutely_15"]["precipitation"],
            "freq":    "15min"
        })
    else:
        dfm = pd.DataFrame(columns=dfh.columns)

    # waves (hourly)
    wt = wav["hourly"]["time"]
    dfw = pd.DataFrame({"time": pd.to_datetime(wt),
                        "wave_m": wav["hourly"]["wave_height"]})

    # Prefer 15-min where available, then hourly after the last 15-min ts
    df = pd.concat([dfm, dfh[dfh["time"] > dfm["time"].max()] if not dfm.empty else dfh],
                   ignore_index=True)

    # Merge waves
    df = df.merge(dfw, on="time", how="left")

    # Daytime filter (times are already local due to timezone param)
    df["local_hour"] = df["time"].dt.hour
    df = df[(df["local_hour"] >= DAY_START) & (df["local_hour"] <= DAY_END)].copy()

    # Direction + constraints
    df.dropna(inplace=True)
    df["dir_lbl"] = df["dir_deg"].apply(deg_to_16pt)
    df["dir_ok"]  = df["dir_deg"].apply(lambda d: direction_in_sector(d, spot_meta.get("dir_sector")))
    df["rain_ok"] = df["precip"] <= RAIN_LIMIT
    df["speed_ok"] = df["wind_kn"] >= 12.0
    df["valid"]   = df["dir_ok"] & df["rain_ok"] & df["speed_ok"]
    df["band"]    = df["wind_kn"].apply(classify_band)

    df["kiteable"] = df["valid"]
    df["spot"] = name

    return df[[
        "spot","time","wind_kn","gust_kn","dir_deg","dir_lbl",
        "precip","wave_m","band","kiteable"
    ]].sort_values("time")

# ---------- 5) Fetch model updates (AROME HD hourly + 15-min) ----------
def fetch_model_updates():
    """
    Reads latest completed run metadata from Open-Meteo Open Data S3.
    See: data_spatial/<model>/latest.json (documented by Open-Meteo).
    """
    base = "https://openmeteo.s3.amazonaws.com/data_spatial"
    models = {
        "meteofrance_arome_france_hd": "AROME France HD (hourly)",
        "meteofrance_arome_france_hd_15min": "AROME France HD (15-min)"
    }
    out = {}
    for m, title in models.items():
        url = f"{base}/{m}/latest.json"
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            j = r.json()
            # Be lenient about field names:
            # Common keys include: "run" (ISO), "timestamps", "variables", etc.
            run_iso = j.get("reference_time")
            last_modified_time = j.get("last_modified_time")
            # Best effort: ensure ISO8601 formatting (keep as-is if already ISO)
            out[m] = {
                "title": title,
                "run": run_iso,
                "last_modified_time": last_modified_time,
                "source": url
            }
        except Exception as e:
            out[m] = {
                "title": title,
                "run": None,
                "source": url,
                "error": str(e)
            }
    return out


def main():
    os.makedirs("out", exist_ok=True)
    hourly, min15, waves = fetch_weather(SPOTS)
    model_updates = fetch_model_updates()
    Lh, Lm15, Lw = map(as_locations, (hourly, min15, waves))


    all_rows = []
    for i, spot in enumerate(SPOTS):
        df = build_df(spot["name"], spot, Lh[i], Lm15[i], Lw[i])
        all_rows.append(df)
    full = pd.concat(all_rows, ignore_index=True)

    # ---------- JSON payload (preserve SPOTS order) ----------
    result = []
    for spot_meta in SPOTS:
        spot_name = spot_meta["name"]
        g = full[full["spot"] == spot_name]
        rows = []
        for _, r in g.iterrows():
            rows.append({
                "time": r["time"].isoformat(),
                "wind_kn": float(r["wind_kn"]),
                "gust_kn": float(r["gust_kn"]),
                "dir_deg": float(r["dir_deg"]),
                "dir": r["dir_lbl"],
                "precip_mm_h": float(r["precip"]),
                "wave_m": None if pd.isna(r["wave_m"]) else float(r["wave_m"]),
                "band": r["band"],
                "kiteable": bool(r["kiteable"]),
            })
        result.append({"spot": spot_name, "rows": rows})

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model_updates": model_updates,
        "spots": result  # <-- preserves SPOTS order
    }
    with open("out/windows.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Wrote out/windows.json")

if __name__ == "__main__":
    main()
