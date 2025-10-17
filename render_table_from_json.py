# render_table_from_json.py
import json, os
from datetime import datetime
from collections import defaultdict

IN_FILE = "out/windows.json"
OUT_FILE = "out/report.html"

# ---- star rating (0..5) based on your wind bands; 0 if not kiteable ----
def stars_for(row):
    if not row.get("kiteable", False):
        return 0
    w = row["wind_kn"]
    if w >= 25: return 5
    if w >= 20: return 4
    if w >= 17: return 3
    if w >= 15: return 2
    if w >= 12: return 1
    return 0

def stars_str(n):
    return "★" * n + "☆" * (5 - n)

# Optional: badge for extreme wind
def extreme_badge(band: str):
    band = band.lower()
    if band == "too much": return "⚠️ too much"
    if band in ("hardcore", "insane"): return "🔥 " + band
    return ""

def fmt_precip(mm_h: float):
    return f"{mm_h:.1f} mm/h" if mm_h and mm_h > 0 else ""

def fmt_wave(wave_m):
    if wave_m is None:
        return ""
    return f"{wave_m:.1f} m"

def parse_time(iso: str):
    return datetime.fromisoformat(iso)

def main():
    os.makedirs("out", exist_ok=True)
    with open(IN_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # data produced by kite_windows_json_only.py now looks like:
    # { generated_at: ..., model_updates: {...}, spots: [ {spot, rows:[...]} , ... ] }
    spots = [entry["spot"] for entry in data["spots"]]

    # Build lookup: spot -> time -> row
    by_spot_time = defaultdict(dict)
    all_times = set()
    for entry in data["spots"]:
        spot = entry["spot"]
        for r in entry["rows"]:
            t = r["time"]
            by_spot_time[spot][t] = r
            all_times.add(t)

    # Sorted time columns
    times_sorted = sorted(all_times, key=parse_time)

    css = """
    <style>
      :root { --fg:#111; --muted:#777; --grid:#eaeaea; }
      body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,sans-serif;margin:20px;color:var(--fg)}
      h1{margin:0 0 10px 0;font-size:18px}
      .legend{margin-bottom:12px;color:var(--muted);font-size:13px}
      table{border-collapse:collapse;width:max-content;min-width:100%}
      th, td{border:1px solid var(--grid);padding:8px 10px;vertical-align:top}
      th{background:#fafafa;position:sticky;top:0;z-index:2}
      .spotcol{position:sticky;left:0;background:#fff;z-index:1}
      .cell{line-height:1.25; min-width:140px}
      .muted{color:var(--muted)}
      .stars{font-size:13px;letter-spacing:1px}
      .badge{display:inline-block;background:#0000000d;border-radius:6px;padding:0 6px;margin-left:6px;font-size:12px}
      .ok {background:#f6fff6}
      .no {background:#fafafa}
      .great {background:#f0fff0}
      .nowrap{white-space:nowrap}
      .topbar{display:flex;gap:18px;align-items:baseline;flex-wrap:wrap}
      .updates{font-size:12px;color:var(--muted)}
    </style>
    """

    def cell_html(row):
        if not row:
            return "<div class='muted'>—</div>"

        wind = f"{row['wind_kn']:.0f}/{row['gust_kn']:.0f} kt"
        direc = f"{row['dir']}"  # label only
        precip = fmt_precip(row["precip_mm_h"])
        wave = fmt_wave(row["wave_m"]) if row["wind_kn"] >= 12 else ""
        s = stars_for(row)
        badge = extreme_badge(row["band"])
        kval = "✅" if row.get("kiteable") else "<span class='muted'>—</span>"
        badge_html = f"<span class='badge'>{badge}</span>" if badge else ""
        return (
            f"<div class='cell'>"
            f"<div><strong>{wind}</strong> {badge_html}</div>"
            f"<div>{direc}</div>"
            f"{f'<div>🌧 {precip}</div>' if precip else ''}"
            f"{f'<div>🌊 {wave}</div>' if wave else ''}"
            f"<div class='stars'>{stars_str(s)} {kval}</div>"
            f"</div>"
        )

    def cell_class(row):
        if not row:
            return ""
        b = row["band"].lower()
        if b in ("great", "very good", "insane", "hardcore"):
            return "great"
        if b in ("good", "ok", "light"):
            return "ok" if row.get("kiteable") else "no"
        return "no"

    # Top bar with generation time and model run info (if present)
    updates_bits = []
    mu = data.get("model_updates") or {}
    for key, info in mu.items():
        run = info.get("run")
        if run:
            updates_bits.append(f"{info.get('title', key)}: <span class='nowrap'>{run}</span>")
    updates_html = " • ".join(updates_bits) if updates_bits else "—"

    html = []
    html.append("<!doctype html><meta charset='utf-8'><title>Kite conditions</title>")
    html.append(css)
    html.append("<div class='topbar'>")
    html.append("<h1>Kite conditions (AROME 15-min + hourly, local 06:00–20:00)</h1>")
    html.append(f"<div class='updates'>Model runs: {updates_html}</div>")
    html.append("</div>")
    html.append("<div class='legend'>Rows: spots • Columns: local date & time. Cells show wind/gust, direction, rain only if present, waves only if wind ≥ 12 kt, and a 0–5 ★ rating.</div>")

    # Table: first column = spot, subsequent columns = datetimes
    html.append("<table>")
    # Header
    html.append("<thead><tr><th class='spotcol'>Spot</th>")
    for t in times_sorted:
        dt = parse_time(t)
        html.append(f"<th class='nowrap'>{dt:%Y-%m-%d %H:%M}</th>")
    html.append("</tr></thead><tbody>")

    # Rows per spot
    for s in spots:
        html.append(f"<tr><td class='spotcol'><strong>{s}</strong></td>")
        for t in times_sorted:
            row = by_spot_time[s].get(t)
            html.append(f"<td class='{cell_class(row)}'>{cell_html(row)}</td>")
        html.append("</tr>")

    html.append("</tbody></table>")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"Wrote {OUT_FILE}")

if __name__ == "__main__":
    main()