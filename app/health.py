"""Symbolic medical astrology section («Ιατρική αστρολογία (συμβολική)») assembled from the Greek library app/library/health.json.

Nothing here is a diagnosis: texts speak of «τάση» (tendency) and «ευαίσθητο σημείο» (sensitive point). The module only assembles:
  1. body map (12 signs + planets, SVG with highlighted signs)         2. chart-specific watch points
  3. age timeline 0-90 (slow-planet transits, cycles, progressions) + the next 10 years     4. Chinese five-element layer + Pythagorean numbers
Edit the Greek in app/library/health.json, not here."""
from __future__ import annotations
import math
from datetime import datetime, timezone
import numpy as np
from .reading import lib, cap
from .engine import astro, transits as T
from .bodymap import svg_bodymap, GLYPH

RULER = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus",
         "Scorpio": "Pluto", "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Uranus", "Pisces": "Neptune"}
BODY_PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"]
HARD_PLANETS = ["Saturn", "Mars", "Pluto", "Neptune", "Uranus"]            # also the priority order when two of them meet
ASPECT_KEY = {0: "conjunction", 90: "square", 180: "opposition", 270: "square"}
ASPECT_GLYPH = {"conjunction": "☌", "square": "□", "opposition": "☍"}
BAND_EDGES = [0, 15, 30, 45, 60, 75, 200]
BAND_CAP = 7                      # max ordinary transit windows per age band (all milestones are always shown)
TRANSIT_ORB = {"Saturn": 2.0, "Uranus": 1.5, "Neptune": 1.5, "Pluto": 1.5, "Chiron": 1.5, "Jupiter": 2.0}
SELF_ANGLES = {"Saturn": (0, 90, 180, 270), "Uranus": (0, 90, 180, 270), "Neptune": (90, 180, 270), "Chiron": (0, 90, 180, 270), "Jupiter": (0,)}
W_TRANSIT = {"Pluto": 5, "Saturn": 5, "Uranus": 4, "Neptune": 3, "Chiron": 3}
W_TARGET = {"Sun": 3, "Moon": 3, "Asc": 3, "Saturn": 2, "H6": 3, "H6R": 2}
W_ANGLE = {0: 1.2, 180: 1.1, 90: 1.0, 270: 1.0}


def _fmt(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def _tight(o: float) -> str:
    L = lib("health")["tightness"]
    return L["very"] if o < 1 else L["tight"] if o < 3 else L["mid"] if o < 5.5 else L["wide"]


def _cusp(chart, h):
    c = chart.get("cusps") or {}
    return c.get(h, c.get(str(h)))


def _sign_of(lon):
    return astro.split_deg(lon)["sign"]


# ============================================================== 1. body map
def body_map(chart: dict, tk: bool) -> dict:
    H, S, P = lib("health"), lib("signs"), lib("planets")
    marks: dict[str, list[str]] = {}
    pl = chart["planets"]

    def mark(sign, why):
        marks.setdefault(sign, []).append(why)
    mark(pl["Sun"]["sign"], "Ήλιος")
    if tk or not chart.get("moon_sign_uncertain"):
        mark(pl["Moon"]["sign"], "Σελήνη")
    if tk:
        mark(chart["ascendant_pos"]["sign"], "Ωροσκόπος")
        c6 = _cusp(chart, 6)
        if c6 is not None:
            mark(_sign_of(c6), "6ος οίκος")
    if "Chiron" in pl:
        mark(pl["Chiron"]["sign"], "Χείρων")
    signs = []
    for k in astro.SIGNS:
        d = H["signs"][k]
        signs.append({"key": k, "name": S[k]["name"], "glyph": GLYPH[k], "areas": d["areas"], "tendency": d["tendency"], "care": d["care"],
                      "marks": marks.get(k, [])})
    planets = []
    for k in BODY_PLANETS:
        if k not in pl:
            continue
        d, p = H["planets"][k], pl[k]
        planets.append({"key": k, "name": P[k]["name"], "glyph": P[k]["glyph"], "areas": d["areas"], "theme": d["theme"], "tendency": d["tendency"],
                        "tip": d["tip"], "sign": S[p["sign"]]["name"], "sign_in": S[p["sign"]]["in"], "house": p.get("house") if tk else None})
    return {"signs": signs, "planets": planets, "svg": svg_bodymap(set(marks))}


# ============================================================== 2. watch points
def _areas(sign_or_planet: dict, n: int | None = None) -> str:
    a = sign_or_planet["areas"]
    return ", ".join(a[:n] if n else a)


def watch_points(chart: dict, tk: bool) -> tuple[list[dict], list[str]]:
    H, S, P = lib("health"), lib("signs"), lib("planets")
    pl = chart["planets"]; items: list[dict] = []; skipped: list[str] = []
    G = H["groups"]

    def add(group, title, area, tendency, tip, tightness=None):
        items.append({"group": group, "group_name": G[group], "title": title, "area": area, "tendency": tendency.strip(), "tightness": tightness, "tip": tip})

    # --- core: Ascendant (+ruler), Sun, Moon
    if tk:
        a = chart["ascendant_pos"]["sign"]; sd = H["signs"][a]
        R = RULER[a]; rp = pl[R]
        txt = H["core"]["asc"].format(**{"in": S[a]["in"], "areas": _areas(sd)}) + sd["tendency"] + " "
        txt += H["core"]["asc_ruler"].format(ruler=H["planets"][R]["nom"], ruler_in=S[rp["sign"]]["in"],
                                              ruler_house=f", στον {rp['house']}ο οίκο" if rp.get("house") else "", ruler_areas=_areas(H["planets"][R], 3))
        add("core", f"Ωροσκόπος {S[a]['in']} · κυβερνήτης: {P[R]['name']}", f"{_areas(sd, 3)} · {_areas(H['planets'][R], 2)}", txt, sd["care"])
    else:
        skipped.append("Ωροσκόπος και κυβερνήτης του (χωρίς ώρα γέννησης δεν υπολογίζονται).")
    s = pl["Sun"]["sign"]; sd = H["signs"][s]
    add("core", f"Ήλιος {S[s]['in']}", f"{_areas(sd, 3)} · {_areas(H['planets']['Sun'], 2)}",
        H["core"]["sun"].format(**{"in": S[s]["in"], "areas": _areas(sd)}) + sd["tendency"], sd["care"] + " " + H["planets"]["Sun"]["tip"])
    m = pl["Moon"]["sign"]; md = H["signs"][m]
    mt = H["core"]["moon"].format(**{"in": S[m]["in"], "areas": _areas(md)}) + md["tendency"]
    if not tk and chart.get("moon_sign_uncertain"):
        mt = H["core"]["moon_uncertain"] + mt
    add("core", f"Σελήνη {S[m]['in']}", f"{_areas(md, 3)} · {_areas(H['planets']['Moon'], 2)}", mt, md["care"] + " " + H["planets"]["Moon"]["tip"])

    # --- houses 6, 8, 12
    if tk:
        for h in (6, 8, 12):
            c = _cusp(chart, h)
            if c is None:
                continue
            hs = _sign_of(c); hd = H["houses"][str(h)]; sd = H["signs"][hs]
            inh = [k for k in BODY_PLANETS if k in pl and pl[k].get("house") == h]
            txt = hd["intro"] + f" Η αρχή του οίκου στο δικό σου χάρτη είναι {S[hs]['in']}: {_areas(sd)}. "
            if inh:
                txt += "Εδώ βρίσκονται: " + "; ".join(f"{H['planets'][k]['nom']} {S[pl[k]['sign']]['in']} ({_areas(H['planets'][k], 3)})" for k in inh) + ". "
                lead = next((k for k in HARD_PLANETS + ["Chiron"] if k in inh), inh[0])
                txt += H["planets"][lead]["tendency"] + " "
            else:
                txt += hd["empty"] + " "
            if h == 6:
                R = RULER[hs]; rp = pl[R]
                txt += f"Ο κυβερνήτης του οίκου ({P[R]['name']}) βρίσκεται {S[rp['sign']]['in']}" + (f", στον {rp['house']}ο οίκο" if rp.get("house") else "") + "."
            area = f"{_areas(sd, 3)}" + (" · " + ", ".join(P[k]["name"] for k in inh) if inh else "")
            add("houses", hd["title"], area, txt, hd["tip"] + " " + sd["care"])
    else:
        skipped.append("6ος, 8ος και 12ος οίκος (χωρίς ώρα γέννησης δεν υπολογίζονται οίκοι).")

    # --- hard aspects from the natal chart
    A = lib("aspects"); ph = H["aspect_phrases"]
    ok_names = set(BODY_PLANETS) | ({"Ascendant"} if tk else set())
    if not tk:
        ok_names.discard("Moon")
        skipped.append("Όψεις που αφορούν τη Σελήνη (η θέση της είναι αβέβαιη χωρίς ώρα γέννησης).")
    found = []
    for a in chart["aspects"]:
        if a["type"] not in ph or a["orb"] > 5.0:
            continue
        x, y = a["a"], a["b"]
        if x not in ok_names or y not in ok_names or not (x in HARD_PLANETS or y in HARD_PLANETS):
            continue
        if x in HARD_PLANETS and y in HARD_PLANETS:
            prim, sec = sorted((x, y), key=HARD_PLANETS.index)
        else:
            prim, sec = (x, y) if x in HARD_PLANETS else (y, x)
        found.append((a, prim, sec))
    for a, prim, sec in found[:8]:
        pd, sd = H["planets"][prim], H["planets"][sec]
        txt = (f"{cap(pd['nom'])} {ph[a['type']]} {sd['acc']}. Συμβολικά, συναντιούνται τα θέματα «{_areas(pd, 3)}» και «{_areas(sd, 3)}», "
               f"και η ένταση ανάμεσά τους ζητά προσοχή. {pd['tendency']}")
        add("aspects", f"{P[prim]['name']} {ASPECT_GLYPH[a['type']]} {P[sec]['name']}", f"{_areas(pd, 3)} · {_areas(sd, 3)}", txt, pd["tip"],
            f"{_tight(a['orb'])} ({_fmt(a['orb'])}°)")
    if not found:
        skipped.append("Δεν βρέθηκαν στενές δύσκολες όψεις (σύνοδος, τετράγωνο, διάμετρος μέχρι 5°) με τον Κρόνο, τον Άρη, τον Πλούτωνα, τον Ποσειδώνα ή τον Ουρανό.")

    # --- element balance
    el = chart["balance"]["elements"]; n = chart["balance"]["n"]; lo = min(el.values()); EL = H["elements"]
    W = lib("misc")["west_elements"]; any_el = False
    for k, v in el.items():
        kind = "excess" if (v >= 5 or (v >= 4 and v - lo >= 3)) else "lack" if v <= 1 else None
        if kind:
            any_el = True
            d = EL[k][kind]
            add("elements", d["title"], d["area"], d["tendency"], d["tip"], f"{W[k]['name']}: {v} από {n} σημεία του χάρτη")
    if not any_el:
        d = EL["balanced"]
        add("elements", d["title"], d["area"], d["tendency"], d["tip"])

    # --- Chiron
    if "Chiron" in pl:
        c = pl["Chiron"]; cs = c["sign"]; sd = H["signs"][cs]
        txt = H["chiron"]["text"].format(**{"in": S[cs]["in"], "areas": _areas(sd)}) + sd["tendency"] + " "
        if tk and c.get("house"):
            txt += H["chiron"]["house"].format(house=c["house"], where=lib("houses")[str(c["house"])]["where"]) + " "
        txt += H["chiron"]["tip_extra"]
        add("chiron", f"Χείρων {S[cs]['in']}" + (f" · {c['house']}ος οίκος" if tk and c.get("house") else ""), _areas(sd, 3), txt, H["planets"]["Chiron"]["tip"] + " " + sd["care"])
    return items, skipped


# ============================================================== 3. age timeline
def _dt(jd: float) -> datetime:
    return astro.timescale().tt_jd(jd).utc_datetime()


def _my(jd: float) -> str:
    d = _dt(jd)
    return f"{lib('health')['timeline']['months'][d.month - 1]} {d.year}"


def _row(birth_jd, kind, prio, j0, j1, exact, title, what, areas, watch, tip, extra=None):
    d0, d1 = _dt(j0), _dt(j1)
    a0, a1 = (j0 - birth_jd) / T.YEAR, (j1 - birth_jd) / T.YEAR
    a0, a1 = float(max(a0, 0.0)), float(max(a1, 0.0))
    ra0, ra1 = int(round(a0)), int(round(a1))
    ex = ""
    if exact:
        ex = ", ".join(_my(e) for e in exact) + f" (~{int(round((exact[0] - birth_jd) / T.YEAR))} ετών)"
    row = {"kind": kind, "prio": prio, "jd0": j0, "jd1": j1, "age_from": round(a0, 2), "age_to": round(a1, 2),
           "age_text": f"{ra0}" if ra0 == ra1 else f"{ra0}–{ra1}",
           "years": f"{d0.year}" if d0.year == d1.year else f"{d0.year}–{d1.year}",
           "dates": _my(j0) if _my(j0) == _my(j1) else f"{_my(j0)} – {_my(j1)}",
           "exact": ex, "title": title, "what": what, "areas": areas, "watch": watch, "tip": tip}
    if extra:
        row.update(extra)
    return row


def _band(age: float) -> int:
    for i in range(6):
        if BAND_EDGES[i] <= age < BAND_EDGES[i + 1]:
            return i
    return 5


def timeline(chart: dict, tk: bool, today: datetime) -> dict:
    H, S, P = lib("health"), lib("signs"), lib("planets")
    TL = H["timeline"]
    birth = chart["jd_tt"]
    grid = T.life_grid(birth, 90.0, 1.0)
    pl = chart["planets"]
    lons = {k: T.lon_at(k, grid) for k in ("Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron")}
    notes = []
    if "Chiron" not in pl:
        lons["Chiron"] = np.full(len(grid), np.nan)
    if np.isnan(lons["Chiron"]).any() and "Chiron" in pl:
        notes.append(TL["chiron_limit"])
    if not tk:
        notes.append(TL["no_time"])

    # ---- natal targets
    targets: dict[str, dict] = {}
    targets["Sun"] = {"lon": pl["Sun"]["lon"], **TL["target"]["Sun"]}
    targets["Saturn"] = {"lon": pl["Saturn"]["lon"], **TL["target"]["Saturn"]}
    if tk:
        targets["Moon"] = {"lon": pl["Moon"]["lon"], **TL["target"]["Moon"]}
        targets["Asc"] = {"lon": chart["ascendant"], **TL["target"]["Asc"]}
        c6 = _cusp(chart, 6); s6 = _sign_of(c6); R = RULER[s6]
        targets["H6"] = {"lon": c6, "acc": TL["target"]["H6"]["acc"].format(sign=S[s6]["name"]), "short": TL["target"]["H6"]["short"],
                         "areas": TL["target"]["H6"]["areas"].format(areas=_areas(H["signs"][s6], 3))}
        tag = " (κυβερνήτης του 6ου οίκου)"
        rd = H["planets"][R]
        if R in ("Sun", "Moon", "Saturn"):
            targets[R]["acc"] += tag
            targets[R]["w_bonus"] = 1
        else:
            targets["H6R"] = {"lon": pl[R]["lon"], "acc": TL["target"]["H6R"]["acc"].format(planet=P[R]["name"]), "short": f"κυβερνήτης 6ου ({P[R]['name']})",
                              "areas": TL["target"]["H6R"]["areas"].format(areas=_areas(rd, 3))}
    rows: list[dict] = []
    # ---- hard transits to natal points
    for tp in ("Saturn", "Uranus", "Neptune", "Pluto", "Chiron"):
        TR = TL["transit"][tp]
        if np.isnan(lons[tp]).all():
            continue
        for tk_, tg in targets.items():
            if tp == "Saturn" and tk_ == "Saturn":
                continue
            for ang in (0, 90, 180, 270):
                for w in T.aspect_windows(grid, lons[tp], tg["lon"], ang, TRANSIT_ORB[tp]):
                    if w["start"] == 0:
                        continue      # already in orb at birth: that is the natal aspect itself (see the watch points), not a new activation
                    at = ASPECT_KEY[ang]
                    prio = W_TRANSIT[tp] * (W_TARGET[tk_] + tg.get("w_bonus", 0)) * W_ANGLE[ang]
                    title = f"{TR['nom']} {ASPECT_GLYPH[at]} {tg['short']}"
                    what = f"Ο {TR['nom']} {H['aspect_phrases'][at]} {tg['acc']}"
                    rows.append(_row(birth, "transit", prio, grid[w["start"]], grid[w["end"]], w["exact"], title, what,
                                     f"{TR['areas']} · {tg['areas']}", f"{TR['watch']} {TL['aspect_note'][at]}", TR["tip"]))
    # ---- self aspects / returns = milestones
    for tp, angles in SELF_ANGLES.items():
        if tp not in pl or np.isnan(lons[tp]).all():
            continue
        for ang in angles:
            for w in T.aspect_windows(grid, lons[tp], pl[tp]["lon"], ang, TRANSIT_ORB[tp]):
                if ang == 0 and w["start"] == 0:
                    continue          # the natal position itself
                at = ASPECT_KEY[ang]; ms = TL["milestone"].get(f"{tp}_{at}")
                if not ms:
                    continue
                rows.append(_row(birth, "milestone" if tp != "Jupiter" else "cycle", 100, grid[w["start"]], grid[w["end"]], w["exact"], ms["title"], ms["text"],
                                 TL["milestone_areas"][tp], ms["text"], TL["milestone_tip"][tp]))
    # ---- nodal returns
    nl = T.lon_at("MeanNode", grid)
    nat = float(T.lon_at("MeanNode", np.array([birth]))[0])
    ms = TL["milestone"]["node_return"]
    for w in T.aspect_windows(grid, nl, nat, 0, 2.0):
        if w["start"] == 0:
            continue
        rows.append(_row(birth, "cycle", 100, grid[w["start"]], grid[w["end"]], w["exact"], ms["title"], ms["text"], TL["milestone_areas"]["node_return"], ms["text"],
                         TL["milestone_tip"]["node_return"]))
    # ---- progressed milestones
    for ev in T.progressed_events(birth, pl["Moon"]["lon"] if tk else None):
        k = ev["kind"]; ms = TL["milestone"][k]; j = birth + ev["age"] * T.YEAR
        what, title = ms["text"], ms["title"]
        if k == "prog_sun_ingress":
            sg = astro.SIGNS[ev["sign_index"]]
            fm = {"in": S[sg]["in"], "areas": _areas(H["signs"][sg], 3)}
            what, title = what.format(**fm), title.format(**fm)
        rows.append(_row(birth, "cycle", 90, j - 0.25 * T.YEAR, j + 0.25 * T.YEAR, [j], title, what, TL["milestone_areas"][k], what, TL["milestone_tip"][k]))
    # ---- slow planets crossing the 6th house
    if tk:
        c6, c7 = _cusp(chart, 6), _cusp(chart, 7)
        for tp in ("Saturn", "Uranus", "Neptune", "Pluto"):
            for w in T.house_windows(grid, lons[tp], c6, c7):
                nom = TL["transit"][tp]["nom"]; ht = TL["house_transit"]
                rows.append(_row(birth, "house", 16 if tp == "Saturn" else 12, grid[w["start"]], grid[w["end"]], None, ht["title"].format(nom=nom),
                                 ht["long"].format(nom=f"Ο {nom}"), f"{ht['areas']} · {TL['transit'][tp]['areas']}", TL["transit"][tp]["watch"], TL["transit"][tp]["tip"]))
    rows.sort(key=lambda r: (r["jd0"], -r["prio"]))

    # ---- age bands
    bands = []
    for i in range(6):
        inb = [r for r in rows if _band(r["age_from"]) == i]
        always = [r for r in inb if r["kind"] in ("milestone", "cycle")]
        ordinary = sorted([r for r in inb if r["kind"] not in ("milestone", "cycle")], key=lambda r: -r["prio"])[:BAND_CAP]
        sel = sorted(always + ordinary, key=lambda r: r["jd0"])
        bands.append({"label": TL["bands"][i], "name": TL["band_names"][i], "rows": [_public(r) for r in sel], "total": len(inb)})

    # ---- next 10 years (all windows)
    today_jd = astro.timescale().from_datetime(today.astimezone(timezone.utc)).tt
    start = max(today_jd, birth); end = start + 10 * T.YEAR
    nxt = [r for r in rows if r["jd1"] >= start and r["jd0"] <= end]
    ten = [_public(r) for r in nxt]
    by_year = []
    for y in range(today.year, today.year + 11):
        y0 = astro.timescale().utc(y, 1, 1).tt; y1 = astro.timescale().utc(y + 1, 1, 1).tt
        if y1 < start or y0 > end:
            continue
        act = [r["title"] for r in rows if r["jd1"] >= y0 and r["jd0"] < y1]
        by_year.append({"year": y, "age": int(y - _dt(birth).year), "items": act})
    # ---- lunar return
    lunar = TL["lunar_unknown"]
    if tk:
        j = T.next_lunar_return(max(today_jd, birth), pl["Moon"]["lon"])
        if j:
            d = _dt(j)
            lunar = TL["lunar"].format(date=f"{d.day} {TL['months_full'][d.month - 1]} {d.year}")
    return {"intro": TL["intro"], "method": TL["method"].format(cap=BAND_CAP), "notes": notes, "bands": bands,
            "next10": {"from": _dt(start).strftime("%Y-%m-%d"), "to": _dt(end).strftime("%Y-%m-%d"), "rows": ten, "by_year": by_year}, "lunar": lunar,
            "counts": {"rows_total": len(rows)}}


def _public(r: dict) -> dict:
    return {k: v for k, v in r.items() if k not in ("jd0", "jd1", "prio")}


# ============================================================== 4. Chinese layer + numbers
def chinese_layer(ch: dict) -> dict:
    H = lib("health")["chinese"]; C = lib("chinese")["elements"]
    cnt = ch["element_count"]; n = sum(cnt.values())
    strong_at = math.ceil(n * 0.4)
    rows, tips = [], []
    for k in ("wood", "fire", "earth", "metal", "water"):
        v = cnt[k]; d = H["elements"][k]
        st = "strong" if v >= strong_at else "absent" if v == 0 else "light" if v == 1 else "ok"
        text = d["strong"] if st == "strong" else d["weak"] if st in ("absent", "light") else ""
        if st in ("strong", "absent", "light"):
            tips.append({"element": C[k]["name"], "tip": d["tip"]})
        rows.append({"key": k, "name": C[k]["name"], "cn": C[k]["cn"], "organs": d["organs"], "emotion": d["emotion"], "tissue": d["tissue"], "count": v,
                     "status": st, "status_label": H["status"][st], "text": text})
    dm = ch["day_master"]["element"]
    out = {"title": H["title"], "intro": H["intro"], "n": n, "rows": rows, "tips": tips,
           "balanced": H["balanced"] if all(r["status"] in ("ok", "light") for r in rows) and not any(r["status"] in ("strong", "absent") for r in rows) else None,
           "day_master": H["day_master"].format(el=C[dm]["name"], organs=H["elements"][dm]["organs"]), "note": H["note"]}
    return out


def numbers_layer(num: dict) -> dict:
    H = lib("health")["numbers"]
    items = []
    for key in ("life_path", "destiny", "personal_year"):
        v = num.get(key)
        if v is None:
            continue
        d = H["values"].get(str(v))
        if not d:
            continue
        role = H["roles"][key].format(year=num.get("personal_year_for", ""))
        items.append({"role": role, "value": v, "theme": d["theme"], "tip": d["tip"]})
    return {"title": H["title"], "note": H["note"], "items": items}


# ============================================================== assemble
def generate(chart: dict, chinese: dict, numerology: dict, today: datetime | None = None) -> dict:
    H = lib("health"); tk = chart["time_known"]
    today = today or datetime.now(timezone.utc)
    if today.tzinfo is None:
        today = today.replace(tzinfo=timezone.utc)
    watch, skipped = watch_points(chart, tk)
    notes = []
    if not tk:
        notes.append("Δεν δόθηκε ώρα γέννησης: παραλείπονται τα σημεία που αφορούν τον Ωροσκόπο και τους οίκους (6ος, 8ος, 12ος). Όσα αφορούν τον Ήλιο, τους πλανήτες, τα στοιχεία και τους πυλώνες εμφανίζονται κανονικά.")
    notes.append(H["rulers_note"])
    out = {"title": H["title"], "disclaimer_top": H["disclaimer_top"], "science_note": H["science_note"], "checkup": H["checkup"], "stoic": H["stoic"], "intro": H["intro"],
           "disclaimer_bottom": H["disclaimer_bottom"], "time_known": tk, "notes": notes,
           "bodymap": body_map(chart, tk), "watch": watch, "watch_skipped": skipped,
           "timeline": timeline(chart, tk, today), "chinese": chinese_layer(chinese), "numbers": numbers_layer(numerology)}
    out["chat_lines"] = chat_lines(out)
    return out


def chat_lines(h: dict) -> list[str]:
    L = ["Υγεία (συμβολική ενότητα, όχι διάγνωση): σημεία προσοχής: " + "; ".join(f"{w['title']} ({w['area']})" for w in h["watch"][:7]) + "."]
    nx = h["timeline"]["next10"]["rows"]
    if nx:
        L.append("Επόμενα 10 χρόνια (συμβολικά παράθυρα): " + "; ".join(f"{r['years']} {r['title']}" for r in nx[:6]) + ".")
    c = h["chinese"]
    strong = [r["name"] for r in c["rows"] if r["status"] == "strong"]; weak = [r["name"] for r in c["rows"] if r["status"] == "absent"]
    L.append("Κινεζικά στοιχεία: έντονα: " + (", ".join(strong) or "κανένα") + "· λείπουν: " + (", ".join(weak) or "κανένα") + ".")
    L.append("Κανόνας για την ενότητα υγείας: μίλα μόνο για συμβολικές «τάσεις» και «ευαίσθητα σημεία»· καμία διάγνωση, πρόγνωση ασθένειας, συμπλήρωμα, δοσολογία ή θεραπεία· πάντα προτείνεις τακτικό έλεγχο και γιατρό για συμπτώματα· η αστρολογία δεν έχει επιστημονική απόδειξη για την υγεία.")
    return L
