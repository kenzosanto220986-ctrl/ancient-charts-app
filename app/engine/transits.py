"""Slow-planet transits across a life (ages 0-90), vectorised with numpy and fast (~50 ms per chart, a few MB of RAM).

Positions of Jupiter..Pluto come from a pre-computed 2-day table (app/data/transit_table.npz, JPL DE440s, 1900-2150; see
tools/build_transit_table.py), interpolated linearly (error < 0.01 deg). Chiron comes from the existing JPL Horizons table (1900-2100,
cubic Hermite, vectorised here). Progressed Sun/Moon use the normal Skyfield ephemeris (only ~90 days after birth are needed).
All times are Julian Days (TT); age = (jd - birth_jd) / 365.2425."""
from __future__ import annotations
from functools import lru_cache
import numpy as np
from . import astro

YEAR = 365.2425
DATA = astro.DATA
TABLE_BODIES = ("Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")


@lru_cache(1)
def _table():
    z = np.load(DATA / "transit_table.npz")
    return float(z["start_tt"]), float(z["step"]), {k: z[k] for k in TABLE_BODIES}


@lru_cache(1)
def _chiron_arrays():
    jds, lons, m = astro._chiron_table()
    return np.asarray(jds), np.asarray(lons), np.asarray(m)


def table_range():
    start, step, tab = _table()
    n = len(next(iter(tab.values())))
    return start, start + step * (n - 1)


def lon_at(name: str, jd) -> np.ndarray:
    """Geocentric ecliptic longitude (deg, 0-360) of a slow body at Julian Days `jd` (array). NaN outside the table range."""
    jd = np.atleast_1d(np.asarray(jd, dtype=float))
    if name == "Chiron":
        jds, lons, m = _chiron_arrays()
        i = np.clip(np.searchsorted(jds, jd, side="right") - 1, 0, len(jds) - 2)
        h = jds[i + 1] - jds[i]
        t = (jd - jds[i]) / h
        h00 = 2 * t**3 - 3 * t**2 + 1; h10 = t**3 - 2 * t**2 + t; h01 = -2 * t**3 + 3 * t**2; h11 = t**3 - t**2
        out = (h00 * lons[i] + h10 * h * m[i] + h01 * lons[i + 1] + h11 * h * m[i + 1]) % 360
        out[(jd < jds[0]) | (jd > jds[-1])] = np.nan
        return out
    if name == "MeanNode":
        T = (jd - 2451545.0) / 36525.0
        return (125.04452 - 1934.136261 * T) % 360
    start, step, tab = _table()
    arr = tab[name]
    x = (jd - start) / step
    out = np.interp(x, np.arange(len(arr)), arr) % 360
    out[(x < 0) | (x > len(arr) - 1)] = np.nan
    return out


def _runs(mask: np.ndarray):
    """Start/end indices (inclusive) of True runs."""
    if not mask.any():
        return []
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0] - 1))


def _merge(runs, gap):
    out = []
    for s, e in runs:
        if out and s - out[-1][1] <= gap:
            out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def aspect_windows(jd: np.ndarray, lon: np.ndarray, natal: float, angle: float, orb: float, merge_days: int = 500):
    """Windows in which transiting `lon` is within `orb` of natal+angle. Returns list of dicts with indices into jd:
    start, end (first/last index inside the orb), exact (list of jd of exact passes, up to 3), min_orb."""
    d = (lon - natal - angle + 180) % 360 - 180
    ok = np.isfinite(d)
    mask = ok & (np.abs(np.nan_to_num(d, nan=999)) <= orb)
    wins = []
    for s, e in _merge(_runs(mask), merge_days):
        seg = d[s:e + 1]
        passes = []
        sc = np.where((np.sign(seg[:-1]) * np.sign(seg[1:]) < 0) & (np.abs(seg[:-1]) < 90) & (np.abs(seg[1:]) < 90))[0]
        for k in sc:
            a, b = seg[k], seg[k + 1]
            passes.append(float(jd[s + k] + (jd[s + k + 1] - jd[s + k]) * a / (a - b)))
        if not passes:
            passes = [float(jd[s + int(np.nanargmin(np.abs(seg)))])]
        wins.append({"start": int(s), "end": int(e), "exact": passes[:3], "min_orb": float(np.nanmin(np.abs(seg)))})
    return wins


def life_grid(birth_jd: float, years: float = 90.0, step: float = 1.0):
    return birth_jd + np.arange(0.0, years * YEAR + step, step)


def house_windows(jd, lon, cusp_a: float, cusp_b: float, merge_days=300):
    inside = ((lon - cusp_a) % 360) < ((cusp_b - cusp_a) % 360)
    inside &= np.isfinite(lon)
    return [{"start": int(s), "end": int(e)} for s, e in _merge(_runs(inside), merge_days)]


# ------------------------------------------------------------ progressions / lunations
def _sun_moon(jd, chunk: int = 500):
    """Apparent ecliptic-of-date longitudes of Sun and Moon at jd (array) using the main (DE421) ephemeris.
    Processed in chunks: Skyfield allocates large temporary arrays, chunking keeps the peak at ~20 MB."""
    ts = astro.timescale(); e = astro.eph()
    jd = np.atleast_1d(np.asarray(jd, dtype=float))
    sun, moon = [], []
    for i in range(0, len(jd), chunk):
        t = ts.tt_jd(jd[i:i + chunk])
        for body, acc in (("sun", sun), ("moon", moon)):
            acc.append(np.asarray(e["earth"].at(t).observe(e[body]).apparent().ecliptic_latlon(epoch="date")[1].degrees) % 360)
    return np.concatenate(sun), np.concatenate(moon)


def _crossings(x: np.ndarray, y: np.ndarray, target: float):
    """x positions where angle y crosses `target` (deg), moving forward."""
    d = (y - target + 180) % 360 - 180
    k = np.where((d[:-1] < 0) & (d[1:] >= 0) & (np.abs(d[:-1]) < 90))[0]
    return [float(x[i] + (x[i + 1] - x[i]) * (-d[i]) / (d[i + 1] - d[i])) for i in k]


def progressed_events(birth_jd: float, natal_moon: float | None, years: float = 90.0):
    """Secondary progressions (1 day = 1 year). Returns list of dicts {age, kind, sign?}. Moon events only if natal_moon is given."""
    ages = np.arange(0.0, years + 0.0001, 0.02)
    sun, moon = _sun_moon(birth_jd + ages)
    ev = []
    si = (sun // 30).astype(int)
    for i in np.where(np.diff(si) != 0)[0]:
        ev.append({"age": float(ages[i + 1]), "kind": "prog_sun_ingress", "sign_index": int(si[i + 1] % 12)})
    elong = (moon - sun) % 360
    for a in _crossings(ages, elong, 0.0):
        ev.append({"age": a, "kind": "prog_new_moon"})
    for a in _crossings(ages, elong, 180.0):
        ev.append({"age": a, "kind": "prog_full_moon"})
    if natal_moon is not None:
        for a in _crossings(ages, moon, natal_moon):
            if a > 1:
                ev.append({"age": a, "kind": "prog_moon_return"})
    ev.sort(key=lambda x: x["age"])
    return ev


def next_lunar_return(from_jd: float, natal_moon: float, days: float = 32.0):
    """JD (TT) of the next time the transiting Moon returns to the natal Moon longitude, or None."""
    jd = from_jd + np.arange(0.0, days, 1 / 24)
    _, moon = _sun_moon(jd)
    c = _crossings(jd, moon, natal_moon)
    return c[0] if c else None
