"""Glue: form input -> timezone -> chart + Chinese pillars + numerology + reading + SVG wheel."""
from __future__ import annotations
from datetime import datetime, date, time as dtime, timezone
from .engine import astro, chinese, numerology, geo
from . import reading, wheel

MIN_YEAR, MAX_YEAR = 1900, 2050   # JPL DE421 covers 1899-07-29 .. 2053-10-09; Chiron table 1900-2100


class InputError(ValueError):
    pass


def parse_input(d: dict):
    try:
        y, m, dd = [int(x) for x in str(d.get("date", "")).split("-")]
        bd = date(y, m, dd)
    except Exception:
        raise InputError("Η ημερομηνία γέννησης δεν είναι έγκυρη (μορφή ΕΕΕΕ-ΜΜ-ΗΗ).")
    if not (MIN_YEAR <= bd.year <= MAX_YEAR):
        raise InputError(f"Η εφαρμογή υποστηρίζει ημερομηνίες από {MIN_YEAR} έως {MAX_YEAR}.")
    tstr = d.get("time")
    time_known = bool(tstr) and not d.get("time_unknown")
    if time_known:
        try:
            hh, mm = [int(x) for x in str(tstr).split(":")[:2]]
            t = dtime(hh, mm)
        except Exception:
            raise InputError("Η ώρα γέννησης δεν είναι έγκυρη (μορφή ΩΩ:ΛΛ).")
    else:
        t = dtime(12, 0)
    # place
    city = None
    if d.get("city_id"):
        city = geo.get_city(d["city_id"])
        if not city:
            raise InputError("Δεν βρέθηκε η πόλη. Διάλεξε μία από τη λίστα.")
        lat, lon, tz, place = city["lat"], city["lon"], city["tz"], city["name"] + ", " + city["country"]
    elif d.get("lat") is not None and d.get("lon") is not None:
        try:
            lat, lon = float(d["lat"]), float(d["lon"])
        except Exception:
            raise InputError("Οι συντεταγμένες δεν είναι έγκυρες.")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise InputError("Οι συντεταγμένες είναι εκτός ορίων.")
        tz = d.get("tz") or geo.tz_for_coords(lat, lon)
        place = f"{lat:.2f}, {lon:.2f}"
    else:
        raise InputError("Διάλεξε πόλη γέννησης.")
    return bd, t, time_known, lat, lon, tz, place


def build(d: dict) -> dict:
    bd, t, time_known, lat, lon, tz, place = parse_input(d)
    naive = datetime.combine(bd, t)
    rt = geo.resolve_local_time(tz, naive)
    utc = rt["utc"]
    chart = astro.compute_chart(utc, lat, lon, time_known)
    ch = chinese.four_pillars(utc, naive, lon, time_known)
    name = (d.get("name") or "").strip()[:80] or None
    num = numerology.compute(bd.year, bd.month, bd.day, name)
    rd = reading.generate(chart, ch, num, name)
    D = reading.lib("misc")["disclaimers"]
    warns = []
    for w in rt["warnings"]:
        key = {"gap": "tz_gap", "ambiguous": "tz_ambiguous", "old_date": "tz_old", "lmt": "tz_lmt"}[w]
        warns.append(D[key])
    if bd.year < 1970 and D["tz_old"] not in warns:
        warns.append(D["tz_old"])
    off = rt["offset_hours"]
    sign = "+" if off >= 0 else "-"
    hh, mm = divmod(int(round(abs(off) * 60)), 60)
    tzinfo = {"tz": tz, "utc_offset": f"UTC{sign}{hh}" + (f":{mm:02d}" if mm else ""), "dst": rt["dst"], "abbr": rt["abbr"],
              "utc": utc.strftime("%Y-%m-%d %H:%M"), "warnings": warns}
    return {"input": {"name": name, "date": bd.isoformat(), "time": t.strftime("%H:%M") if time_known else None, "place": place,
                      "lat": round(lat, 4), "lon": round(lon, 4)},
            "timezone": tzinfo, "chart": _clean(chart), "chinese": ch, "numerology": num, "reading": rd,
            "svg": wheel.svg_wheel(chart), "time_known": time_known}


def _clean(chart):
    out = dict(chart)
    if "cusps" in chart:
        out["cusps"] = {str(k): v for k, v in chart["cusps"].items()}
    return out
