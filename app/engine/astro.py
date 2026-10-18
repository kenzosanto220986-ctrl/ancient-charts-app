"""Western chart calculation: JPL DE421 via Skyfield, tropical zodiac (true equinox of date),
true node (osculating), Chiron (JPL Horizons table, interpolated), Placidus houses, aspects.

Adapted from earlier ephemeris scripts.
(same formulas for Ascendant/MC/Placidus; positions now use the ecliptic of date)."""
from __future__ import annotations
import csv, math, bisect
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from skyfield.api import load
from skyfield.framelib import true_equator_and_equinox_of_date
from skyfield.nutationlib import iau2000b_radians, mean_obliquity

DATA = Path(__file__).resolve().parent.parent / "data"
rad, deg = math.radians, math.degrees

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
ELEMENTS = ["fire", "earth", "air", "water"]            # sign index % 4
MODALITIES = ["cardinal", "fixed", "mutable"]            # sign index % 3

BODIES = {
    "Sun": "sun", "Moon": "moon", "Mercury": "mercury", "Venus": "venus", "Mars": "mars",
    "Jupiter": "jupiter barycenter", "Saturn": "saturn barycenter", "Uranus": "uranus barycenter",
    "Neptune": "neptune barycenter", "Pluto": "pluto barycenter",
}
PLANET_ORDER = list(BODIES) + ["TrueNode", "Chiron"]

_ts = load.timescale()
_eph = None


def eph():
    global _eph
    if _eph is None:
        _eph = load(str(DATA / "de421.bsp"))
    return _eph


def timescale():
    return _ts


def split_deg(lon: float):
    lon %= 360
    s = int(lon // 30)
    d = lon - 30 * s
    m = int(d % 1 * 60)
    return {"sign_index": s, "sign": SIGNS[s], "deg": int(d), "min": m, "in_sign": d}


def fmt(lon: float) -> str:
    x = split_deg(lon)
    return f"{x['deg']}°{x['min']:02d}' {x['sign']}"


def ang_diff(a: float, b: float) -> float:
    """Signed shortest difference a-b in (-180, 180]."""
    return (a - b + 180) % 360 - 180


# ---------------------------------------------------------------- Chiron
@lru_cache(1)
def _chiron_table():
    jds, lons = [], []
    seen = set()
    with open(DATA / "chiron.csv") as f:
        r = csv.reader(f)
        next(r)
        for date, lon in r:
            if date in seen:
                continue
            seen.add(date)
            dt = datetime.strptime(date, "%Y-%b-%d %H:%M")
            jds.append(_ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute).tt)
            lons.append(float(lon))
    order = sorted(range(len(jds)), key=lambda i: jds[i])
    jds = [jds[i] for i in order]
    lons = [lons[i] for i in order]
    # unwrap
    for i in range(1, len(lons)):
        while lons[i] - lons[i - 1] > 180: lons[i] -= 360
        while lons[i] - lons[i - 1] < -180: lons[i] += 360
    # tangents (central differences)
    n = len(jds)
    m = []
    for i in range(n):
        a, b = max(i - 1, 0), min(i + 1, n - 1)
        m.append((lons[b] - lons[a]) / (jds[b] - jds[a]))
    return jds, lons, m


def chiron_lon(jd_tt: float):
    """Returns (longitude, speed deg/day) or None outside 1900-2100."""
    jds, lons, m = _chiron_table()
    if not (jds[0] <= jd_tt <= jds[-1]):
        return None
    i = min(max(bisect.bisect_right(jds, jd_tt) - 1, 0), len(jds) - 2)
    h = jds[i + 1] - jds[i]
    t = (jd_tt - jds[i]) / h
    h00 = 2 * t**3 - 3 * t**2 + 1; h10 = t**3 - 2 * t**2 + t; h01 = -2 * t**3 + 3 * t**2; h11 = t**3 - t**2
    lon = h00 * lons[i] + h10 * h * m[i] + h01 * lons[i + 1] + h11 * h * m[i + 1]
    # derivative
    d00 = 6 * t**2 - 6 * t; d10 = 3 * t**2 - 4 * t + 1; d01 = -6 * t**2 + 6 * t; d11 = 3 * t**2 - 2 * t
    sp = (d00 * lons[i] + d10 * h * m[i] + d01 * lons[i + 1] + d11 * h * m[i + 1]) / h
    return lon % 360, sp


# ---------------------------------------------------------------- positions
def _lon_of(t, name):
    e = eph()
    p = e["earth"].at(t).observe(e[BODIES[name]]).apparent()
    return float(p.ecliptic_latlon(epoch="date")[1].degrees)


def true_obliquity(t) -> float:
    """True obliquity of date, radians."""
    dpsi, deps = iau2000b_radians(t)
    return rad(float(mean_obliquity(t.tdb)) / 3600.0) + float(deps)


def true_node(t) -> tuple[float, float]:
    """Osculating (true) ascending node of the Moon's geocentric orbit, ecliptic of date.
    Returns (longitude, speed deg/day)."""
    def node(tt):
        e = eph()
        p = e["earth"].at(tt).observe(e["moon"])
        x, v = p.frame_xyz_and_velocity(true_equator_and_equinox_of_date)
        eps = true_obliquity(tt)
        c, s = math.cos(eps), math.sin(eps)
        rx, ry, rz = (float(q) for q in x.au)
        vx, vy, vz = (float(q) for q in v.au_per_d)
        # rotate equator -> ecliptic of date
        r = (rx, c * ry + s * rz, -s * ry + c * rz)
        w = (vx, c * vy + s * vz, -s * vy + c * vz)
        hx = r[1] * w[2] - r[2] * w[1]
        hy = r[2] * w[0] - r[0] * w[2]
        return float(deg(math.atan2(hx, -hy)) % 360)
    n0 = node(t)
    n1 = node(_ts.tt_jd(t.tt + 0.25))
    return n0, float(ang_diff(n1, n0) / 0.25)


def planet_positions(t, with_chiron=True):
    out = {}
    for name in BODIES:
        l0 = _lon_of(t, name)
        l1 = _lon_of(_ts.tt_jd(t.tt + 0.1), name)
        l2 = _lon_of(_ts.tt_jd(t.tt - 0.1), name)
        sp = ang_diff(l1, l2) / 0.2
        out[name] = {"lon": float(l0), "speed": float(sp)}
    n, sp = true_node(t)
    out["TrueNode"] = {"lon": n, "speed": sp}
    if with_chiron:
        c = chiron_lon(t.tt)
        if c:
            out["Chiron"] = {"lon": c[0], "speed": c[1]}
    for name, d in out.items():
        d["retrograde"] = d["speed"] < 0 and name != "TrueNode"
        d.update(split_deg(d["lon"]))
    return out


# ---------------------------------------------------------------- angles & houses
def _asc_mc(ramc_deg, lat_deg, eps):
    R, phi = rad(ramc_deg), rad(lat_deg)
    mc = deg(math.atan2(math.sin(R), math.cos(R) * math.cos(eps))) % 360
    asc = deg(math.atan2(math.cos(R), -(math.sin(R) * math.cos(eps) + math.tan(phi) * math.sin(eps)))) % 360
    return asc, mc


def houses(t, lat, lon):
    """Placidus cusps (dict 1..12 -> longitude), asc, mc, system name used."""
    eps = true_obliquity(t)
    ramc = float((t.gast * 15 + lon) % 360)
    asc, mc = _asc_mc(ramc, lat, eps)
    phi = rad(lat)
    lfr = lambda ra: deg(math.atan2(math.sin(rad(ra)), math.cos(rad(ra)) * math.cos(eps))) % 360
    polar = abs(lat) > 66.0
    system = "Placidus"
    cusps = {}
    if not polar:
        def plac(frac, night=False):
            ra = (ramc + (180 - frac * 90 if night else frac * 90)) % 360
            for _ in range(200):
                l = lfr(ra)
                dec = math.asin(math.sin(eps) * math.sin(rad(l)))
                ad = deg(math.asin(max(-1, min(1, math.tan(dec) * math.tan(phi)))))
                new = (ramc + (180 - frac * (90 - ad) if night else frac * (90 + ad))) % 360
                if abs(ang_diff(new, ra)) < 1e-9:
                    ra = new
                    break
                ra = new
            return lfr(ra)
        cusps = {1: asc, 10: mc, 11: plac(1 / 3), 12: plac(2 / 3), 2: plac(2 / 3, True), 3: plac(1 / 3, True)}
    else:  # Placidus undefined near polar circles -> Porphyry fallback
        system = "Porphyry"
        if (asc - mc) % 360 > 180:      # near the polar circle the horizon/meridian intersection flips; use the opposite point
            asc = (asc + 180) % 360
        arc = (asc - mc) % 360
        cusps = {1: asc, 10: mc, 11: (mc + arc / 3) % 360, 12: (mc + 2 * arc / 3) % 360}
        arc2 = (((mc + 180) % 360) - asc) % 360
        cusps[2] = (asc + arc2 / 3) % 360
        cusps[3] = (asc + 2 * arc2 / 3) % 360
    for k in (1, 2, 3, 10, 11, 12):
        cusps[(k + 5) % 12 + 1] = (cusps[k] + 180) % 360
    return cusps, asc, mc, system


def house_of(lon, cusps):
    for k in range(1, 13):
        s, e = cusps[k], cusps[k % 12 + 1]
        if (lon - s) % 360 < (e - s) % 360:
            return k
    return 1


# ---------------------------------------------------------------- aspects
ASPECTS = {"conjunction": (0, 8), "sextile": (60, 5), "square": (90, 7), "trine": (120, 7), "opposition": (180, 8)}
REDUCED = {"TrueNode", "Chiron", "Ascendant", "MC"}


def find_aspects(points: dict):
    """points: name -> {'lon','speed'(optional)}. Returns list sorted by orb."""
    names = list(points)
    res = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if {a, b} == {"Ascendant", "MC"}:
                continue
            d = abs(ang_diff(points[a]["lon"], points[b]["lon"]))
            for aname, (angle, orb) in ASPECTS.items():
                lim = orb - (2 if (a in REDUCED or b in REDUCED) else 0)
                if a in ("Sun", "Moon") or b in ("Sun", "Moon"):
                    lim += 1 if aname in ("conjunction", "opposition", "trine", "square") else 0
                o = abs(d - angle)
                if o <= lim:
                    sa, sb = points[a].get("speed"), points[b].get("speed")
                    applying = None
                    if sa is not None and sb is not None and a not in ("Ascendant", "MC"):
                        # separation rate: positive -> widening
                        rate = (sa - sb) * (1 if ang_diff(points[a]["lon"], points[b]["lon"]) >= 0 else -1)
                        widening = rate > 0
                        gap_above = d > angle
                        applying = (not widening) if gap_above else widening
                    res.append({"a": a, "b": b, "type": aname, "angle": angle, "orb": round(float(o), 2),
                                "tight": bool(o < 3.0), "applying": None if applying is None else bool(applying)})
    res.sort(key=lambda x: x["orb"])
    return res


# ---------------------------------------------------------------- moon phase
def moon_phase(t):
    e = eph()
    s = e["earth"].at(t).observe(e["sun"]).apparent().ecliptic_latlon(epoch="date")[1].degrees
    m = e["earth"].at(t).observe(e["moon"]).apparent().ecliptic_latlon(epoch="date")[1].degrees
    elong = (m - s) % 360
    idx = int(((elong + 22.5) % 360) // 45)
    illum = (1 - math.cos(rad(elong))) / 2 * 100
    keys = ["new", "waxing_crescent", "first_quarter", "waxing_gibbous", "full", "waning_gibbous", "last_quarter", "waning_crescent"]
    return {"key": keys[idx], "elongation": round(float(elong), 1), "illumination": int(round(float(illum)))}


# ---------------------------------------------------------------- full chart
def compute_chart(utc_dt: datetime, lat: float, lon: float, time_known: bool = True):
    """utc_dt: naive or aware UTC datetime. For unknown time pass local-noon UTC with time_known=False."""
    t = _ts.utc(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour, utc_dt.minute, utc_dt.second)
    planets = planet_positions(t)
    chart = {"planets": planets, "time_known": time_known, "moon_phase": moon_phase(t), "jd_tt": float(t.tt)}
    if time_known:
        cusps, asc, mc, system = houses(t, lat, lon)
        chart.update(cusps={k: v for k, v in cusps.items()}, ascendant=asc, mc=mc, house_system=system)
        for name, p in planets.items():
            p["house"] = house_of(p["lon"], cusps)
        pts = {n: {"lon": p["lon"], "speed": p["speed"]} for n, p in planets.items()}
        pts["Ascendant"] = {"lon": asc}
        pts["MC"] = {"lon": mc}
    else:
        pts = {n: {"lon": p["lon"], "speed": p["speed"]} for n, p in planets.items()}
    chart["aspects"] = find_aspects(pts)
    # balance (10 planets + Ascendant when known)
    el = {k: 0 for k in ELEMENTS}; mo = {k: 0 for k in MODALITIES}
    count_pts = [p["sign_index"] for n, p in planets.items() if n in BODIES]
    if time_known:
        count_pts.append(split_deg(asc)["sign_index"])
    for s in count_pts:
        el[ELEMENTS[s % 4]] += 1; mo[MODALITIES[s % 3]] += 1
    chart["balance"] = {"elements": el, "modalities": mo, "n": len(count_pts)}
    # Moon uncertainty when time unknown: does the Moon change sign during the local-noon +-12h window?
    if not time_known:
        a = split_deg(_lon_of(_ts.tt_jd(t.tt - 0.5), "Moon"))["sign_index"]
        b = split_deg(_lon_of(_ts.tt_jd(t.tt + 0.5), "Moon"))["sign_index"]
        chart["moon_sign_uncertain"] = a != b
    for k in ("ascendant", "mc"):
        if k in chart:
            chart[k + "_pos"] = split_deg(chart[k])
    return chart
