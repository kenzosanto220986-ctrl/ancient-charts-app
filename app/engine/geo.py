"""Offline city search (geonamescache, cities >5000 inhabitants) and historical timezone resolution (zoneinfo/tzdata)."""
from __future__ import annotations
import bisect, unicodedata
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.casefold())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("ς", "σ").replace("ʻ", "").replace("'", "").replace("-", " ").strip()


def _has_greek(s):
    return any("\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff" for c in s)


@lru_cache(1)
def _index():
    import geonamescache
    gc = geonamescache.GeonamesCache(min_city_population=5000)
    cities = gc.get_cities()
    countries = gc.get_countries()
    states = gc.get_us_states()
    keys = []  # (normalized name, -population, id)
    meta = {}
    for gid, c in cities.items():
        names = {c["name"]} | set(c.get("alternatenames", []))
        gr = next((n for n in c.get("alternatenames", []) if _has_greek(n)), None)
        country = countries.get(c["countrycode"], {}).get("name", c["countrycode"])
        admin = states.get(c["admin1code"], {}).get("name") if c["countrycode"] == "US" else None
        meta[gid] = {"id": int(gid), "name": c["name"], "name_el": gr, "country": country, "cc": c["countrycode"], "admin": admin,
                     "lat": c["latitude"], "lon": c["longitude"], "tz": c["timezone"], "pop": c["population"]}
        seen = set()
        for n in names:
            k = norm(n)
            if len(k) >= 2 and k not in seen:
                seen.add(k)
                keys.append((k, -c["population"], gid))
    keys.sort()
    return keys, meta


def search_cities(q: str, limit: int = 8):
    q = norm(q)
    if len(q) < 2:
        return []
    keys, meta = _index()
    i = bisect.bisect_left(keys, (q,))
    found = {}
    while i < len(keys) and keys[i][0].startswith(q):
        k, negpop, gid = keys[i]
        exact = k == q
        score = (0 if exact else 1, negpop)
        if gid not in found or score < found[gid]:
            found[gid] = score
        i += 1
    ranked = sorted(found.items(), key=lambda kv: kv[1])[:limit]
    out = []
    for gid, _ in ranked:
        m = dict(meta[gid])
        label = m["name"] + (f" ({m['name_el']})" if m["name_el"] and m["name_el"] != m["name"] else "")
        label += ", " + (m["admin"] + ", " if m["admin"] else "") + m["country"]
        m["label"] = label
        out.append(m)
    return out


def get_city(city_id) -> dict | None:
    _, meta = _index()
    return meta.get(str(city_id))


def tz_for_coords(lat: float, lon: float) -> str:
    from timezonefinder import TimezoneFinder
    return TimezoneFinder().timezone_at(lat=lat, lng=lon) or "UTC"


def resolve_local_time(tzname: str, naive: datetime) -> dict:
    """Resolve a civil local time to UTC with the historical rules in tzdata (incl. DST).
    Returns dict(utc, offset_hours, abbr, dst, warnings[], tz)."""
    z = ZoneInfo(tzname)
    w = []
    a = naive.replace(tzinfo=z, fold=0)
    b = naive.replace(tzinfo=z, fold=1)
    oa, ob = a.utcoffset(), b.utcoffset()
    chosen = a
    if oa != ob:
        # either ambiguous (clocks turned back) or in a gap (clocks sprung forward)
        rt = a.astimezone(timezone.utc).astimezone(z).replace(tzinfo=None)
        if rt != naive:
            w.append("gap")        # this wall-clock time never existed
        else:
            w.append("ambiguous")  # happened twice; first occurrence used
    off = chosen.utcoffset()
    utc = (naive - off)
    dst = chosen.dst() or timedelta(0)
    if naive.year < 1900:
        w.append("old_date")
    if off.total_seconds() % 900 != 0:
        w.append("lmt")            # local mean time (no standardised zone yet)
    return {"utc": utc, "offset_hours": off.total_seconds() / 3600, "abbr": chosen.tzname(), "dst": dst != timedelta(0),
            "dst_hours": dst.total_seconds() / 3600, "warnings": w, "tz": tzname}
