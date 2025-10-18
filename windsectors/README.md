# Wind Sectors Visualization

This directory contains tools for visualizing wind sectors for various spots defined in the project's configuration.

## plot_wind_sectors.py

This script generates a visual representation of wind sectors for all spots defined in `config.json`. Each spot's wind sector is plotted on a polar coordinate system where:

- 0° represents North
- 90° represents East
- 180° represents South
- 270° represents West

### Features

- Visualizes wind sectors for each spot in a polar plot
- Handles both wrapped and non-wrapped sectors:
  - Wrapped sectors: sectors that cross through North (e.g., 315° to 45°)
  - Non-wrapped sectors: sectors that don't cross through North (e.g., 45° to 90°)
- Uses meteorological wind direction convention (direction wind is coming from)
- Different colors for each spot to distinguish between sectors

### Output

The script generates a `wind_sectors.png` file that shows all wind sectors overlaid on a single polar plot, making it easy to:
- Verify wind sector configurations
- Compare sectors between different spots
- Identify any potential configuration errors

### Usage

```bash
python plot_wind_sectors.py
```

The script reads spot configurations from `config.json` and automatically generates the visualization.
