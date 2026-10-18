"""Chinese Four Pillars (BaZi) - year/month by solar terms (Lichun boundary), day by Julian Day Number.
Solar terms come from the real Sun longitude (DE421). Hour pillar is given for the CLOCK time and for TRUE SOLAR time."""
from __future__ import annotations
import math
from datetime import datetime, timedelta
from .astro import eph, timescale

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
STEM_PY = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
BRANCH_PY = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
ANIMALS = ["rat", "ox", "tiger", "rabbit", "dragon", "snake", "horse", "goat", "monkey", "rooster", "dog", "pig"]
STEM_ELEMENT = ["wood", "wood", "fire", "fire", "earth", "earth", "metal", "metal", "water", "water"]
BRANCH_ELEMENT = ["water", "earth", "wood", "wood", "earth", "fire", "fire", "earth", "metal", "metal", "earth", "water"]
# month branches start at Lichun (Sun 315 deg) = 寅
MONTH_TERMS = [315, 345, 15, 45, 75, 105, 135, 165, 195, 225, 255, 285]  # 寅 卯 辰 巳 午 未 申 酉 戌 亥 子 丑
MONTH_BRANCH_IDX = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0, 1]
TERM_NAMES = ["Λιτσούν (Lichun)", "Τζινγκτζέ (Jingzhe)", "Τσινγκμίνγκ (Qingming)", "Λιξιά (Lixia)", "Μανγκτζόνγκ (Mangzhong)",
              "Σιάοσου (Xiaoshu)", "Λιτσίου (Liqiu)", "Μπαϊλού (Bailu)", "Χανλού (Hanlu)", "Λιντόνγκ (Lidong)", "Ντασιέ (Daxue)", "Σιάοχαν (Xiaohan)"]


def pillar(stem_i: int, branch_i: int):
    return {"stem": STEMS[stem_i % 10], "branch": BRANCHES[branch_i % 12], "stem_i": stem_i % 10, "branch_i": branch_i % 12,
            "text": STEMS[stem_i % 10] + BRANCHES[branch_i % 12],
            "pinyin": f"{STEM_PY[stem_i % 10]} {BRANCH_PY[branch_i % 12]}",
            "stem_element": STEM_ELEMENT[stem_i % 10], "branch_element": BRANCH_ELEMENT[branch_i % 12],
            "yang": stem_i % 2 == 0, "animal": ANIMALS[branch_i % 12]}


def sun_lon(t) -> float:
    e = eph()
    return float(e["earth"].at(t).observe(e["sun"]).apparent().ecliptic_latlon(epoch="date")[1].degrees)


def _solar_year_and_month(utc: datetime):
    """Return (bazi_year, month_number 0..11 from Lichun)."""
    t = timescale().utc(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)
    L = sun_lon(t)
    # month index: number of 30-degree steps since 315 deg
    m = int(((L - 315) % 360) // 30)
    # year changes at Lichun (315): if Sun is in 315..360 or 0..~45 region of the NEW year etc.
    # Calendar Jan-Feb before Lichun belong to previous bazi year.
    year = utc.year
    if utc.month <= 2 and 200 < L < 315:  # Jan 1 .. Lichun: still the previous BaZi year
        year -= 1
    return year, m, L


def day_index(y: int, mth: int, d: int) -> int:
    """Index in the 60-cycle for a civil date (Gregorian; proleptic)."""
    a = (14 - mth) // 12
    yy = y + 4800 - a
    mm = mth + 12 * a - 3
    jdn = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    return (jdn - 11) % 60


def _hour_branch(h: int, mi: int) -> int:
    return ((h * 60 + mi + 60) // 120) % 12   # 23:00-00:59 -> 子 (0)


def four_pillars(utc: datetime, local_clock: datetime, lon_deg: float, time_known=True):
    """utc: UTC datetime of birth; local_clock: naive civil clock datetime (with DST as legally used);
    lon_deg: east-positive longitude. Returns dict with pillars and notes."""
    year, m, L = _solar_year_and_month(utc)
    ystem, ybranch = (year - 4) % 10, (year - 4) % 12
    yp = pillar(ystem, ybranch)
    mbranch = MONTH_BRANCH_IDX[m]
    mstem = ((ystem % 5) * 2 + 2 + m) % 10   # 五虎遁: Jia/Ji year -> Bing(2) at 寅
    mp = pillar(mstem, mbranch)
    notes = []

    def day_hour(clock: datetime):
        # day changes at 23:00 (early-Zi convention): after 23:00 the next day's pillar is used
        d = clock + timedelta(hours=1) if clock.hour >= 23 else clock
        di = day_index(d.year, d.month, d.day)
        return di

    res = {"year": yp, "month": mp, "sun_longitude": round(L, 2), "bazi_year": year,
           "month_term": TERM_NAMES[m], "time_known": time_known}
    di = day_hour(local_clock if time_known else local_clock.replace(hour=12, minute=0))
    res["day"] = pillar(di % 10, di % 12)
    if time_known:
        hb = _hour_branch(local_clock.hour, local_clock.minute)
        hstem = ((di % 10 % 5) * 2 + hb) % 10  # 五鼠遁: Jia/Ji day -> Jia(0) at 子
        res["hour_clock"] = pillar(hstem, hb)
        # true solar time = UTC + longitude/15 h + equation of time
        eot = equation_of_time_minutes(utc)
        ts_dt = utc + timedelta(minutes=lon_deg * 4 + eot)
        res["true_solar_time"] = ts_dt.strftime("%H:%M")
        res["equation_of_time_min"] = round(eot, 1)
        dts = day_hour(ts_dt)
        hb2 = _hour_branch(ts_dt.hour, ts_dt.minute)
        hstem2 = ((dts % 10 % 5) * 2 + hb2) % 10
        res["hour_solar"] = pillar(hstem2, hb2)
        res["day_solar"] = pillar(dts % 10, dts % 12)
        res["hour_differs"] = res["hour_solar"]["text"] != res["hour_clock"]["text"]
        res["day_differs"] = res["day_solar"]["text"] != res["day"]["text"]
        if local_clock.hour >= 23 or local_clock.hour < 1:
            notes.append("zi_hour")
    # five-element counts (stems + branch main element; 3 or 4 pillars)
    cnt = {k: 0 for k in ("wood", "fire", "earth", "metal", "water")}
    ps = [yp, mp, res["day"]] + ([res["hour_clock"]] if time_known else [])
    for p in ps:
        cnt[p["stem_element"]] += 1
        cnt[p["branch_element"]] += 1
    res["element_count"] = cnt
    res["day_master"] = {"stem": res["day"]["stem"], "element": res["day"]["stem_element"], "yang": res["day"]["yang"]}
    res["year_animal"] = yp["animal"]; res["year_element"] = yp["stem_element"]
    res["notes"] = notes
    return res


def equation_of_time_minutes(utc: datetime) -> float:
    n = utc.timetuple().tm_yday + (utc.hour + utc.minute / 60) / 24
    B = 2 * math.pi * (n - 81) / 364
    return 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
