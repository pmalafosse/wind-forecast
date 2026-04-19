"""Plotting utilities for wind forecast data."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _plot_df(
    name: str,
    df: Any,  # pd.DataFrame with time, wind_kn, gust_kn columns
    model_run: Optional[str],
    out_dir: Path,
    open_after: bool,
) -> Path:
    """Core plotting logic. Takes a pre-built DataFrame filtered to the desired time range."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    today = df["time"].dt.date.iloc[0] if not df.empty else datetime.now().date()
    try:
        run_dt = datetime.fromisoformat((model_run or "").replace("Z", "+00:00"))
        run_label = run_dt.strftime("Model run: %Y-%m-%d %H:%MZ")
    except Exception:
        run_label = f"Model run: {model_run or 'unknown'}"

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df["time"], df["wind_kn"], "b-o", label="Wind (kn)", linewidth=2, markersize=5)
    ax.plot(df["time"], df["gust_kn"], "r--o", label="Gusts (kn)", linewidth=2, markersize=5)
    ax.fill_between(df["time"], df["wind_kn"], df["gust_kn"], alpha=0.15, color="orange")
    ax.set_title(f"{name} — 15-min AROME ({today})\n{run_label}", fontsize=13)
    ax.set_ylabel("Wind speed (kn)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()

    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    out_path = plots_dir / f"{name.lower().replace(' ', '_')}_15min_today.png"
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved → {out_path}")

    if open_after:
        subprocess.run(["open", str(out_path)], check=False)

    return out_path


def plot_spot_from_rows(
    name: str,
    rows: List[Dict[str, Any]],
    model_run: Optional[str],
    out_dir: Path,
    open_after: bool = False,
) -> Optional[Path]:
    """Plot 15-min wind chart from pre-fetched rows (no API call)."""
    import matplotlib

    matplotlib.use("Agg")

    import pandas as pd

    if not rows:
        print(f"{name}: no 15-min data, skipping plot", file=sys.stderr)
        return None

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"])
    today = datetime.now().date()
    df = df[df["time"].dt.date == today]
    if df.empty:
        print(f"{name}: no 15-min data for today ({today}), skipping plot", file=sys.stderr)
        return None

    return _plot_df(name, df, model_run, out_dir, open_after)


def plot_spot_15min(
    name: str,
    lat: float,
    lon: float,
    out_dir: Path,
    open_after: bool = True,
) -> Path:
    """Fetch and plot 15-min AROME wind/gust for a spot, filtered to today."""
    try:
        import matplotlib.dates as mdates  # noqa: F401
        import matplotlib.pyplot as plt  # noqa: F401
    except ImportError:
        print(
            "matplotlib is required for plotting. Install with:\n"
            "  uv sync  (matplotlib is a core dependency)",
            file=sys.stderr,
        )
        sys.exit(1)

    import pandas as pd

    from .config import load_config
    from .forecast import ForecastClient, fetch_model_run

    config = load_config()
    client = ForecastClient(config)

    rows = client.fetch_spot_15min(lat, lon)
    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"])

    today = datetime.now().date()
    df = df[df["time"].dt.date == today]
    if df.empty:
        print(f"No 15-min data available for today ({today})", file=sys.stderr)
        sys.exit(1)

    print(f"{name}: {len(df)} points, {df['time'].min()} → {df['time'].max()}")
    print(df[["time", "wind_kn", "gust_kn", "dir_deg"]].to_string(index=False))

    model_run = fetch_model_run()
    return _plot_df(name, df, model_run, out_dir, open_after)
