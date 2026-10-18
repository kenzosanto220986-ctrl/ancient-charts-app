"""Build app/data/transit_table.npz: geocentric apparent ecliptic longitude (true equinox of date, unwrapped, degrees)
of Jupiter, Saturn, Uranus, Neptune, Pluto on a 2-day grid, 1900-01-01 .. 2150-01-01, from JPL DE440s
(DE421 stops in 2053; DE440s covers 1849-2150). Used by app/engine/transits.py (age timeline) so the 32 MB kernel need not ship.
Usage:  python tools/build_transit_table.py /path/to/de440s.bsp
        (https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp)"""
import sys, pathlib
import numpy as np
from skyfield.api import load

kernel = sys.argv[1]
eph = load(kernel)
ts = load.timescale()
START, STEP, N = ts.utc(1900, 1, 1).tt, 2.0, int(250 * 365.25 / 2.0)
jd = START + STEP * np.arange(N)
t = ts.tt_jd(jd)
names = {"Jupiter": "jupiter barycenter", "Saturn": "saturn barycenter", "Uranus": "uranus barycenter",
         "Neptune": "neptune barycenter", "Pluto": "pluto barycenter"}
out = {"start_tt": np.array(START), "step": np.array(STEP)}
for k, v in names.items():
    lon = eph["earth"].at(t).observe(eph[v]).apparent().ecliptic_latlon(epoch="date")[1].degrees
    out[k] = np.rad2deg(np.unwrap(np.deg2rad(lon))).astype("float64")
    print(k, out[k][0], out[k][-1], file=sys.stderr)
dst = pathlib.Path(__file__).resolve().parent.parent / "app/data/transit_table.npz"
np.savez_compressed(dst, **out)
print(dst, dst.stat().st_size, file=sys.stderr)
