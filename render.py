# render_table_from_json.py
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from PIL import Image
except Exception:
    Image = None
from collections import defaultdict

IN_FILE = "out/windows.json"
OUT_FILE = "out/report.html"


# ---------------- Helpers ----------------
def stars_for(row):
    if not row or not row.get("kiteable"):
        return 0
    w = row["wind_kn"]
    return (
        5 if w >= 25 else 4 if w >= 20 else 3 if w >= 17 else 2 if w >= 15 else 1 if w >= 12 else 0
    )


def stars_str(n):
    return "★" * n + "☆" * (5 - n)


def extreme_badge(band):
    b = band.lower()
    if b == "too much":
        return "⚠️ too much"
    if b in ("hardcore", "insane"):
        return "🔥 " + b
    return ""


def fmt_precip(p):
    return f"{p:.1f} mm/h" if p and p > 0 else ""


def fmt_wave(w):
    return f"{w:.1f} m" if w is not None else ""


def parse_time(iso):
    return datetime.fromisoformat(iso)


def hour_key(iso):
    d = parse_time(iso)
    return d.replace(minute=0, second=0, microsecond=0)


# ---------------- Main ----------------
def main():
    os.makedirs("out", exist_ok=True)
    with open(IN_FILE, encoding="utf-8") as f:
        data = json.load(f)

    spot_rows = {s["spot"]: s["rows"] for s in data["spots"]}
    spots = [s for s, r in spot_rows.items() if any(x.get("kiteable") for x in r)]
    if not spots:
        print("No kiteable spots.")
        return

    # Build mapping: hour → list of times
    hour_to_times = defaultdict(set)
    kiteable_hours = set()
    for rows in spot_rows.values():
        for r in rows:
            hour = hour_key(r["time"])
            hour_to_times[hour].add(r["time"])
            if r.get("kiteable"):
                kiteable_hours.add(hour)
    hours_sorted = sorted(hour for hour in hour_to_times.keys() if hour in kiteable_hours)
    for h in hours_sorted:
        hour_to_times[h] = sorted(hour_to_times[h], key=parse_time)

    by_spot_time = defaultdict(dict)
    for s, rows in spot_rows.items():
        for r in rows:
            by_spot_time[s][r["time"]] = r

    css = """
    <style>
      body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,sans-serif;margin:20px;color:#111}
      table{border-collapse:collapse;width:max-content;min-width:100%}
      th,td{border:1px solid #eaeaea;padding:8px 10px;vertical-align:top}
      th{background:#fafafa;position:sticky;top:0;z-index:2}
      .spotcol{position:sticky;left:0;background:#fff;z-index:1}
      .cell{min-width:160px;line-height:1.3}
      .muted{color:#777}
      .stars{font-size:13px;letter-spacing:1px}
      .badge{background:#0000000d;border-radius:6px;padding:0 6px;margin-left:6px;font-size:12px}
      .ok{background:#f6fff6}.great{background:#f0fff0}.no{background:#fafafa}
      .details{display:none;margin-top:6px;border-top:1px dashed #eaeaea;font-size:12px}
      td[data-expanded=true] .details{display:block}
      th[data-expanded=true] .expand-btn{background:#eef}
      .chip{display:inline-block;border:1px solid #eaeaea;border-radius:8px;padding:1px 6px;margin:2px 4px 0 0}
      .nowrap{white-space:nowrap}
      .updates{font-size:12px;color:#777;margin-bottom:6px}
    </style>
    """

    def cell_html(rows_in_hour):
        if not rows_in_hour:
            return "<div class='muted'>—</div>"
        best = max(rows_in_hour, key=lambda r: (stars_for(r), r["wind_kn"]))
        w = f"{best['wind_kn']:.0f}/{best['gust_kn']:.0f} kt"
        direc = best["dir"]
        p = fmt_precip(best["precip_mm_h"])
        wv = fmt_wave(best["wave_m"]) if best["wind_kn"] >= 12 else ""
        s = stars_for(best)
        badge = extreme_badge(best["band"])
        badge_html = f"<span class='badge'>{badge}</span>" if badge else ""
        kval = "✅" if best.get("kiteable") else "—"

        # Main summary
        out = f"<div class='cell'><div><strong>{w}</strong> {badge_html}</div><div>{direc}</div>"
        if p:
            out += f"<div>🌧 {p}</div>"
        if wv:
            out += f"<div>🌊 {wv}</div>"
        out += f"<div class='stars'>{stars_str(s)} {kval}</div></div>"

        # Details (15-min)
        det = []
        for r in sorted(rows_in_hour, key=lambda x: x["time"]):
            if parse_time(r["time"]).minute == 0:
                continue  # skip hourly line
            s2 = stars_for(r)
            det.append(
                f"<div><span class='chip'>{parse_time(r['time']).strftime('%H:%M')}</span> "
                f"{r['wind_kn']:.0f}/{r['gust_kn']:.0f} kt {r['dir']} {stars_str(s2)}</div>"
            )
        if det:
            out += "<div class='details'>" + "".join(det) + "</div>"
        return out

    def cell_class(r):
        if not r:
            return ""
        b = r["band"].lower()
        if b in ("great", "very good", "insane", "hardcore"):
            return "great"
        if b in ("good", "ok", "light"):
            return "ok" if r.get("kiteable") else "no"
        return "no"

    mu = data.get("model_updates") or {}
    updates_html = (
        " • ".join(
            f"{v.get('title', k)}: {v.get('run', '')}" for k, v in mu.items() if v.get("run")
        )
        or "—"
    )

    html = [
        "<!doctype html><meta charset='utf-8'><title>Kite conditions</title>",
        css,
        f"<h1>Kite conditions (AROME 15 min + hourly)</h1><div class='updates'>Model runs: {updates_html}</div>",
        "<table><thead><tr><th class='spotcol'>Spot</th>",
    ]

    # Header: show toggle only if 15-min data exists
    for i, h in enumerate(hours_sorted):
        times = hour_to_times[h]
        label = h.strftime("%Y-%m-%d %H:00")
        has_15 = any(parse_time(t).minute != 0 for t in times)
        btn = f"<button class='expand-btn' data-col='{i}'>Toggle 15 min</button>" if has_15 else ""
        html.append(
            f"<th data-col='{i}' data-expanded='false'><div class='nowrap'>{label}</div>{btn}</th>"
        )
    html.append("</tr></thead><tbody>")

    # Rows per spot
    for s in spots:
        html.append(f"<tr><td class='spotcol'><strong>{s}</strong></td>")
        for i, h in enumerate(hours_sorted):
            times = hour_to_times[h]
            rows = [by_spot_time[s].get(t) for t in times if by_spot_time[s].get(t)]
            best = max(rows, key=lambda r: (stars_for(r), r["wind_kn"])) if rows else None
            html.append(
                f"<td class='{cell_class(best)}' data-col='{i}' data-expanded='false'>{cell_html(rows)}</td>"
            )
        html.append("</tr>")
    html.append("</tbody></table>")

    html.append(
        """
    <script>
      document.addEventListener('click', e => {
        if (!e.target.matches('.expand-btn')) return;
        const col = e.target.dataset.col;
        const th = document.querySelector(`th[data-col="${col}"]`);
        const newState = th.getAttribute('data-expanded') !== 'true';
        th.setAttribute('data-expanded', newState);
        document.querySelectorAll(`td[data-col="${col}"]`).forEach(td =>
          td.setAttribute('data-expanded', newState)
        );
      });
    </script>
    """
    )

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"Wrote {OUT_FILE}")


def find_executable(names):
    """Return first available executable from names or None."""
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    # On macOS, also check common .app bundle locations for Chrome/Chromium
    if sys.platform == "darwin":
        app_candidates = [
            ("google-chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            (
                "google-chrome-stable",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ),
            ("chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
            ("chromium-browser", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
        for name, path in app_candidates:
            if Path(path).exists():
                return path
    return None


def generate_jpg(html_path: str, jpg_path: str, viewport=(2400, 1200)) -> bool:
    """Attempt to render an HTML file to JPG.

    Strategy:
    - Try headless Chrome/Chromium to save a PNG screenshot and convert to JPG.
    - If not available, try wkhtmltoimage directly to produce JPG.
    - Convert PNG->JPG using Pillow if installed, else use macOS `sips`.

    Returns True on success.
    """
    html_p = Path(html_path).absolute()
    out_j = Path(jpg_path).absolute()
    tmp_png = out_j.with_suffix(".png")

    # 1) Try Chrome/Chromium headless
    chrome = find_executable(
        ["google-chrome", "chrome", "chromium", "chromium-browser", "google-chrome-stable"]
    )
    if chrome:
        cmd = [
            chrome,
            "--headless",
            "--disable-gpu",  # Recommended for headless
            f"--window-size={viewport[0]},{viewport[1]}",
            "--hide-scrollbars",  # Remove scrollbars from screenshot
            "--wait-until=networkidle0",  # Wait for page to be fully loaded
            f"--screenshot={str(tmp_png)}",
            f"file://{html_p}",
        ]
        try:
            # Allow seeing any Chrome errors for debugging
            subprocess.check_call(cmd)
            # convert png -> jpg
            return _convert_png_to_jpg(tmp_png, out_j)
        except subprocess.CalledProcessError:
            pass

    # 2) Try wkhtmltoimage
    wk = find_executable(["wkhtmltoimage"])
    if wk:
        try:
            subprocess.check_call([wk, "--quality", "90", str(html_p), str(out_j)])
            return out_j.exists()
        except subprocess.CalledProcessError:
            pass

    # 3) Last resort: open HTML in default browser is not automatable; fail with message
    print(
        "Could not find a renderer (Chrome/Chromium or wkhtmltoimage). Install one to enable JPG generation."
    )
    return False


def _convert_png_to_jpg(png_path: Path, jpg_path: Path) -> bool:
    try:
        if Image:
            img = Image.open(png_path)
            rgb = img.convert("RGB")
            rgb.save(jpg_path, "JPEG", quality=90)
            png_path.unlink(missing_ok=True)
            return True
        # fallback to macOS sips
        if sys.platform == "darwin":
            subprocess.check_call(
                ["sips", "-s", "format", "jpeg", str(png_path), "--out", str(jpg_path)]
            )
            png_path.unlink(missing_ok=True)
            return True
    except Exception:
        pass
    return False


def _parse_args():
    p = argparse.ArgumentParser(description="Render kite forecast HTML and optionally JPG")
    p.add_argument(
        "--jpg",
        nargs="?",
        const="out/report.jpg",
        help="Also generate a JPG from the generated HTML (optional output path)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    main()
    if args.jpg:
        outjpg = args.jpg if isinstance(args.jpg, str) else "out/report.jpg"
        success = generate_jpg(OUT_FILE, outjpg)
        if success:
            print(f"Wrote {outjpg}")
        else:
            print("Failed to generate JPG.")
