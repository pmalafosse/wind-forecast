# wind-forecast
Extract most recent Arome wind forecast

## Setup

### Python Dependencies
Install Pillow (optional, but recommended for better image handling):
```bash
pip install pillow
```

### HTML to Image Renderer
You need at least one of these renderers installed:

#### Option 1: Google Chrome or Chromium (Recommended)
- macOS: 
  - Install Chrome from https://www.google.com/chrome/
  - Or install Chromium via Homebrew: `brew install --cask chromium`
- Linux:
  ```bash
  # Ubuntu/Debian
  sudo apt install chromium-browser
  # Or for Chrome:
  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo apt install ./google-chrome-stable_current_amd64.deb
  ```

#### Option 2: wkhtmltopdf/wkhtmltoimage
- macOS: `brew install wkhtmltopdf`
- Linux: `sudo apt install wkhtmltopdf`

### Image Conversion
For PNG to JPG conversion, the script will use:
1. Pillow (PIL) if installed (recommended, see Python Dependencies above)
2. On macOS: `sips` (built-in, no installation needed)

## Generating JPG Report

After running the report generator (which writes `out/report.html`) you can ask it to also produce a JPG image of the report:

```bash
python render.py --jpg            # creates out/report.jpg
python render.py --jpg my.jpg     # creates my.jpg
```

The script will:
1. Generate the HTML report
2. Use Chrome/Chromium (preferred) or wkhtmltoimage to render it
3. Convert to JPG using Pillow or sips (macOS)

### Troubleshooting

If you see "Could not find a renderer":
1. Check if Chrome/Chromium is installed
2. Try installing wkhtmltoimage as a fallback
3. On macOS, make sure Chrome is in /Applications

For image quality issues:
- Install Pillow for better image conversion: `pip install pillow`
- The viewport size is set to 2400x1200 to capture wide tables
