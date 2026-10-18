"""SVG natal wheel (navy / gold / silver). Ascendant on the left when birth time is known, otherwise 0° Aries on the left."""
from __future__ import annotations
import math
from .engine.astro import SIGNS
from .reading import lib

VS = "\ufe0e"  # force text (non-emoji) presentation
PLANET_GLYPH = {"Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂", "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅",
                "Neptune": "♆", "Pluto": "♇", "TrueNode": "☊", "Chiron": "⚷"}
EL_FILL = {"fire": "#3a2a3f", "earth": "#24323a", "air": "#25304f", "water": "#1f2f55"}
ASP_STYLE = {"conjunction": ("#d4af37", 1.6, ""), "sextile": ("#7fb3ff", 1.1, ""), "trine": ("#7fd1b9", 1.3, ""),
             "square": ("#e07a7a", 1.3, ""), "opposition": ("#e0a45a", 1.3, "")}


def svg_wheel(chart: dict, size: int = 640) -> str:
    cx = cy = size / 2
    R_out, R_sign, R_house, R_pl, R_asp = size * 0.455, size * 0.385, size * 0.29, size * 0.33, size * 0.245
    tk = chart["time_known"]
    rot = chart["ascendant"] if tk else 0.0

    def pt(lon, r):
        a = math.radians((lon - rot) % 360)
        return cx - r * math.cos(a), cy + r * math.sin(a)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" role="img" aria-label="Γενέθλιος χάρτης" class="wheel">',
         f'<defs><radialGradient id="bg" cx="50%" cy="50%" r="60%"><stop offset="0" stop-color="#14224a"/><stop offset="1" stop-color="#0a1230"/></radialGradient></defs>',
         f'<circle cx="{cx}" cy="{cy}" r="{R_out}" fill="url(#bg)" stroke="#d4af37" stroke-width="2"/>']
    # sign ring
    for i in range(12):
        a0, a1 = i * 30, (i + 1) * 30
        x0, y0 = pt(a0, R_out); x1, y1 = pt(a1, R_out); x2, y2 = pt(a1, R_sign); x3, y3 = pt(a0, R_sign)
        el = ["fire", "earth", "air", "water"][i % 4]
        o.append(f'<path d="M{x0:.1f},{y0:.1f} A{R_out},{R_out} 0 0 0 {x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f} A{R_sign},{R_sign} 0 0 1 {x3:.1f},{y3:.1f} Z" fill="{EL_FILL[el]}" stroke="#8d7a3a" stroke-width="0.8"/>')
        gx, gy = pt(a0 + 15, (R_out + R_sign) / 2)
        o.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="sg" text-anchor="middle" dominant-baseline="central">{lib("signs")[SIGNS[i]]["glyph"]}{VS}</text>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{R_sign}" fill="none" stroke="#d4af37" stroke-width="1.2"/>')
    # degree ticks
    for d in range(0, 360, 5):
        x0, y0 = pt(d, R_sign); x1, y1 = pt(d, R_sign - (7 if d % 10 == 0 else 4))
        o.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#c0c8d8" stroke-opacity=".5" stroke-width=".7"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{R_house}" fill="#0b1432" stroke="#c0c8d8" stroke-opacity=".6" stroke-width="1"/>')
    # houses
    if tk:
        cusps = {int(k): v for k, v in chart["cusps"].items()}
        for k in range(1, 13):
            x0, y0 = pt(cusps[k], R_sign); x1, y1 = pt(cusps[k], R_house)
            ang = k in (1, 4, 7, 10)
            o.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{"#d4af37" if ang else "#c0c8d8"}" stroke-opacity="{1 if ang else .45}" stroke-width="{1.8 if ang else .8}"/>')
            mid = cusps[k] + ((cusps[k % 12 + 1] - cusps[k]) % 360) / 2
            tx, ty = pt(mid, R_house - 13)
            o.append(f'<text x="{tx:.1f}" y="{ty:.1f}" class="hn" text-anchor="middle" dominant-baseline="central">{k}</text>')
    # aspect lines
    pts = {n: p["lon"] for n, p in chart["planets"].items()}
    if tk:
        pts["Ascendant"] = chart["ascendant"]; pts["MC"] = chart["mc"]
    for a in chart["aspects"]:
        if a["a"] not in pts or a["b"] not in pts:
            continue
        col, w, dash = ASP_STYLE[a["type"]]
        op = 0.95 if a["tight"] else 0.45
        x0, y0 = pt(pts[a["a"]], R_asp); x1, y1 = pt(pts[a["b"]], R_asp)
        o.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{col}" stroke-opacity="{op}" stroke-width="{w}"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{R_asp}" fill="none" stroke="#c0c8d8" stroke-opacity=".25" stroke-width=".8"/>')
    # planets with de-overlap
    items = sorted(((n, p["lon"]) for n, p in chart["planets"].items()), key=lambda x: x[1])
    disp = {n: l for n, l in items}
    names = [n for n, _ in items]
    for _ in range(80):
        moved = False
        for i in range(len(names)):
            a, b = names[i], names[(i + 1) % len(names)]
            gap = (disp[b] - disp[a]) % 360
            if gap < 8.5:
                push = (8.5 - gap) / 2 + 0.05
                disp[a] = (disp[a] - push) % 360; disp[b] = (disp[b] + push) % 360; moved = True
        if not moved:
            break
    for n in names:
        lon = chart["planets"][n]["lon"]
        x0, y0 = pt(lon, R_sign - 1); x1, y1 = pt(lon, R_sign - 11)
        o.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#d4af37" stroke-width="1.2"/>')
        gx, gy = pt(disp[n], R_pl + 6)
        retro = chart["planets"][n].get("retrograde")
        o.append(f'<text x="{gx:.1f}" y="{gy:.1f}" class="pg" text-anchor="middle" dominant-baseline="central"><title>{lib("planets")[n]["name"]}</title>{PLANET_GLYPH[n]}{VS}</text>')
        dx, dy = pt(disp[n], R_pl - 17)
        sd = chart["planets"][n]["deg"]
        o.append(f'<text x="{dx:.1f}" y="{dy:.1f}" class="pd" text-anchor="middle" dominant-baseline="central">{sd}°{"ᴿ" if retro else ""}</text>')
    if tk:
        for lab, lon in (("AC", chart["ascendant"]), ("MC", chart["mc"])):
            x, y = pt(lon, R_out + 11)
            o.append(f'<text x="{x:.1f}" y="{y:.1f}" class="ang" text-anchor="middle" dominant-baseline="central">{lab}</text>')
    o.append('</svg>')
    return "".join(o)
