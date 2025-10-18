#!/usr/bin/env python3
"""Visualize wind direction sectors for all spots in the configuration."""

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def plot_wind_sectors(spots, output_path="wind_sectors.png"):
    """Create a polar plot of wind direction sectors for all spots."""
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": "polar"})
    ax.set_theta_direction(-1)  # Clockwise
    ax.set_theta_zero_location("N")  # 0° at North

    colors = plt.cm.tab20(np.linspace(0, 1, len(spots)))

    for idx, spot in enumerate(spots):
        name = spot["name"]
        sector = spot["dir_sector"]
        start = float(sector["start"])
        end = float(sector["end"])
        wrap = sector["wrap"]

        # Always plot from start to end, handling wrap
        if wrap:
            if end < start:
                end += 360
            theta = np.linspace(start, end, 200)
            theta = np.mod(theta, 360)
        else:
            if end < start:
                # Swap to ensure positive range
                start, end = end, start
            theta = np.linspace(start, end, 200)

        theta_rad = np.deg2rad(theta)
        r = np.full_like(theta_rad, 1 - idx * 0.06)
        ax.plot(
            theta_rad,
            r,
            lw=10,
            color=colors[idx],
            label=f"{name} ({sector['start']}°→{sector['end']}°)",
        )

    # Compass labels
    angles = np.arange(0, 360, 45)
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ax.set_xticks(np.deg2rad(angles))
    ax.set_xticklabels(labels)
    ax.set_yticks([])
    ax.set_ylim(0, 1.05)
    plt.title("Kiteable Wind Sectors by Spot", pad=20)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()

    out_path = Path(__file__).parent / output_path
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Wind sectors plot saved to {out_path}")


if __name__ == "__main__":
    config = load_config()
    plot_wind_sectors(config["spots"])
