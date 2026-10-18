"""Download a Chiron ecliptic-longitude table (true equinox of date, geocentric, apparent)
from JPL Horizons (public API, no key). Run once; output ships in app/data/chiron.csv.
Step 5 days, 1900-2100; the app interpolates with a cubic Hermite spline (error << 1 arcmin)."""
import re, urllib.request, urllib.parse, sys, pathlib
out = pathlib.Path(__file__).resolve().parent.parent / "app/data/chiron.csv"
rows = []
for y0 in range(1900, 2100, 40):
    q = dict(format="text", COMMAND="'2060'", OBJ_DATA="'NO'", MAKE_EPHEM="'YES'", EPHEM_TYPE="'OBSERVER'",
             CENTER="'500@399'", START_TIME=f"'{y0}-01-01 00:00'", STOP_TIME=f"'{y0+40}-01-06 00:00'",
             STEP_SIZE="'5d'", QUANTITIES="'31'", ANG_FORMAT="'DEG'", CSV_FORMAT="'YES'", TIME_TYPE="'UT'", TIME_DIGITS="'MINUTES'")
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(q)
    txt = urllib.request.urlopen(url, timeout=120).read().decode()
    body = txt.split("$$SOE")[1].split("$$EOE")[0]
    for line in body.strip().splitlines():
        p = [x.strip() for x in line.split(",")]
        # date, flag, flag, lon, lat
        rows.append((p[0], p[3]))
    print(y0, len(rows), file=sys.stderr)
out.write_text("date_ut,ecl_lon_deg\n" + "\n".join(f"{d},{l}" for d, l in rows) + "\n")
