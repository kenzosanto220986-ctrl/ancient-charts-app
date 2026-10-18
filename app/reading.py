"""Template-based Greek reading generator. All prose lives in app/library/*.json (edit those files, not this code)."""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

LIB = Path(__file__).resolve().parent / "library"


@lru_cache(None)
def lib(name: str) -> dict:
    return json.loads((LIB / f"{name}.json").read_text(encoding="utf-8"))


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def deg_text(p: dict) -> str:
    return f"{p['deg']}°{p['min']:02d}′ {lib('signs')[p['sign']]['name']}"


def planet_card(key: str, p: dict, time_known: bool) -> dict:
    pl, sg = lib("planets")[key], lib("signs")[p["sign"]]
    steps = {
        "what": pl["what"],
        "sign": f"{cap(pl['who'])} βρίσκεται {sg['in']} ({deg_text(p)}). {sg['modes'][pl['mode']]}",
    }
    if p.get("retrograde") and pl.get("retro"):
        steps["sign"] += " " + pl["retro"]
    hw = None
    if time_known and p.get("house"):
        h = lib("houses")[str(p["house"])]
        hw = h
        steps["house"] = f"{cap(pl['who'])} βρίσκεται στον {p['house']}ο οίκο. {h['what']} {pl['house_lead']} {h['where']}."
    summ = f"Με μια φράση: {pl['who']} {sg['in']} θέλει να {pl['wants']} {sg['style']}"
    summ += f", κυρίως {hw['short']}." if hw else "."
    steps["summary"] = summ
    return {"key": key, "name": pl["name"], "glyph": pl["glyph"], "sign": sg["name"], "sign_glyph": sg["glyph"],
            "position": deg_text(p), "house": p.get("house"), "retrograde": bool(p.get("retrograde")), "steps": steps}


def angle_card(key: str, lonpos: dict) -> dict:
    pl, sg = lib("planets")[key], lib("signs")[lonpos["sign"]]
    steps = {"what": pl["what"], "sign": f"{cap(pl['who'])} βρίσκεται {sg['in']} ({deg_text(lonpos)}). {sg['modes'][pl['mode']]}",
             "summary": f"Με μια φράση: {pl['who']} {sg['in']} δείχνει {sg['style'].replace('με ', 'ένα ύφος με ', 1)}."}
    return {"key": key, "name": pl["name"], "glyph": pl["glyph"], "sign": sg["name"], "sign_glyph": sg["glyph"],
            "position": deg_text(lonpos), "house": None, "retrograde": False, "steps": steps}


def name_of(k: str) -> str:
    return lib("planets")[k]["name"]


def aspects_text(chart: dict) -> list[dict]:
    out = []
    A, P = lib("aspects"), lib("planets")
    for a in chart["aspects"]:
        if not a["tight"]:
            continue
        t = A[a["type"]]
        txt = f"{cap(P[a['a']]['noun'])} και {P[a['b']]['noun']} {t['verb']}. {t['advice']}"
        mv = {True: "πλησιάζει στην ακρίβεια", False: "απομακρύνεται από την ακρίβεια", None: ""}[a["applying"]]
        out.append({"a": name_of(a["a"]), "b": name_of(a["b"]), "ga": P[a["a"]]["glyph"], "gb": P[a["b"]]["glyph"],
                    "type": t["name"], "glyph": t["glyph"], "orb": a["orb"], "applying": mv, "text": txt})
    return out


def balance_text(chart: dict) -> dict:
    b, W, M = chart["balance"], lib("misc")["west_elements"], lib("misc")["west_modalities"]
    el = b["elements"]; mo = b["modalities"]
    dom_e = max(el, key=el.get); low_e = min(el, key=el.get)
    dom_m = max(mo, key=mo.get); low_m = min(mo, key=mo.get)
    lines = []
    if el[dom_e] >= 4 or el[dom_e] - el[low_e] >= 3:
        lines.append(W[dom_e]["dominant"])
    if el[low_e] <= 1:
        lines.append(W[low_e]["lacking"])
    if mo[dom_m] >= 5:
        lines.append(M[dom_m]["dominant"])
    elif mo[low_m] <= 1:
        lines.append(M[low_m]["lacking"])
    if not lines:
        lines.append("Οι τέσσερις δυνάμεις (φωτιά, γη, αέρας, νερό) είναι σχετικά ισορροπημένες στο χάρτη σου: έχεις πρόσβαση σε πολλούς τρόπους να αντιδράς.")
    return {"elements": {W[k]["name"]: v for k, v in el.items()}, "elements_raw": el,
            "modalities": {M[k]["name"]: v for k, v in mo.items()}, "modalities_raw": mo,
            "dominant_element": W[dom_e]["name"], "lacking_element": W[low_e]["name"], "text": lines}


def chinese_text(ch: dict) -> dict:
    C = lib("chinese")
    an = C["animals"][ch["year_animal"]]; el = C["elements"][ch["year_element"]]
    dm = C["stems"][ch["day"]["stem"]]
    cnt = ch["element_count"]
    lack = [C["elements"][k]["name"] for k, v in cnt.items() if v == 0]
    dom = max(cnt, key=cnt.get)
    lines = [f"{an['name']} {el['gen']} — {an['text']}",
             f"Η ιδιότητά σου «{el['name']}» (από το στέλεχος του έτους) προσθέτει: {el['text']}",
             f"Δώρο: {an['gift']}. Προσοχή: {an['shadow']}. {an['tip']}"]
    sty = {"year": "Έτος", "month": "Μήνας", "day": "Ημέρα"}
    pillars = [{"label": sty[k], "text": ch[k]["text"], "pinyin": ch[k]["pinyin"],
                "stem_element": C["elements"][ch[k]["stem_element"]]["name"], "animal": C["animals"][ch[k]["animal"]]["name"]} for k in ("year", "month", "day")]
    if ch["time_known"]:
        pillars.append({"label": "Ώρα (ρολόι)", "text": ch["hour_clock"]["text"], "pinyin": ch["hour_clock"]["pinyin"],
                        "stem_element": C["elements"][ch["hour_clock"]["stem_element"]]["name"], "animal": C["animals"][ch["hour_clock"]["animal"]]["name"]})
    notes = [lib("misc")["disclaimers"]["chinese_year"]]
    alt = None
    if ch["time_known"]:
        alt = {"label": "Ώρα (αληθινή ηλιακή)", "text": ch["hour_solar"]["text"], "pinyin": ch["hour_solar"]["pinyin"], "solar_time": ch["true_solar_time"],
               "differs": ch["hour_differs"]}
        notes.append(lib("misc")["disclaimers"]["chinese_hour"] + (f" Στη δική σου περίπτωση: ρολόι {ch['hour_clock']['text']}, αληθινή ηλιακή ώρα ~{ch['true_solar_time']} → {ch['hour_solar']['text']}." if ch["hour_differs"] else " Στη δική σου περίπτωση και οι δύο δίνουν την ίδια ώρα."))
        if ch.get("day_differs"):
            notes.append(f"Με αληθινή ηλιακή ώρα, η ημέρα θα ήταν {ch['day_solar']['text']} αντί για {ch['day']['text']}.")
        if "zi_hour" in ch["notes"]:
            notes.append("Γεννήθηκες γύρω από τα μεσάνυχτα (ώρα Ζι): υπάρχουν δύο παραδόσεις για το πότε αλλάζει η ημέρα (23:00 ή 00:00). Εδώ χρησιμοποιείται η αλλαγή στις 23:00.")
    else:
        notes.append("Χωρίς ώρα γέννησης, δεν υπολογίζεται ο Πυλώνας της Ώρας (4ος πυλώνας).")
    return {"title": f"{an['name']} {el['gen']}", "animal": an["name"], "animal_cn": an["cn"], "element": el["name"],
            "pillars": pillars, "hour_alt": alt, "day_master": dm["text"], "day_master_image": dm["image"],
            "element_count": {C["elements"][k]["name"]: v for k, v in cnt.items()},
            "balance_text": (f"Στοιχείο με την πιο έντονη παρουσία: {C['elements'][dom]['name']}." + (f" Λείπει από τους πυλώνες: {', '.join(lack)}. " + " ".join(C['elements'][k]['lack'] for k, v in cnt.items() if v == 0) if lack else "")),
            "text": lines, "notes": notes, "term": ch["month_term"], "sun_longitude": ch["sun_longitude"]}


def numerology_text(n: dict) -> dict:
    N = lib("numbers")
    items = []
    order = ["life_path", "destiny", "soul", "personality", "birthday", "maturity"]
    for k in order:
        if k not in n:
            continue
        v = n[k]
        if not v:
            continue
        r = N["roles"][k]; t = N[str(v)]
        items.append({"key": k, "role": r["name"], "value": v, "intro": r["intro"], "title": t["title"], "text": t["text"],
                      "strength": t["strength"], "challenge": t["challenge"], "tip": t["tip"], "master": v in (11, 22, 33)})
    py = {"value": n["personal_year"], "year": n["personal_year_for"], "text": N["personal_year"][str(n["personal_year"])]}
    notes = ["Η αριθμολογία είναι συμβολική. Χρησιμοποιείται το πυθαγόρειο σύστημα (A=1 … I=9, J=1 … R=9, S=1 … Z=8) με λατινικά γράμματα· οι κύριοι αριθμοί 11, 22, 33 διατηρούνται."]
    if n.get("name_used"):
        notes.append(f"Όνομα που χρησιμοποιήθηκε (λατινικά): {n['name_used']}.")
    else:
        notes.append("Δεν δόθηκε όνομα, οπότε υπολογίστηκαν μόνο οι αριθμοί που βγαίνουν από την ημερομηνία (Μονοπάτι Ζωής, Γενεθλίων, Προσωπικό Έτος).")
    return {"items": items, "personal_year": py, "notes": notes}


def ninety_days(chart: dict, n: dict, ch: dict) -> list[dict]:
    P, S, M, H = lib("misc")["practical"], lib("signs"), lib("misc"), lib("houses")
    moon = chart["planets"]["Moon"]; sun = chart["planets"]["Sun"]; sat = chart["planets"]["Saturn"]
    items = []
    if chart["time_known"] or not chart.get("moon_sign_uncertain"):
        items.append({"phase": "Ημέρες 1–30 · Θεμέλια", "text": P["moon_care"][moon["sign"]]})
    else:
        items.append({"phase": "Ημέρες 1–30 · Θεμέλια", "text": "Βρες μία καθημερινή μικρή συνήθεια φροντίδας (ύπνος, περπάτημα, ήρεμο γεύμα) και κράτησέ την."})
    bal = chart["balance"]["elements"]; low = min(bal, key=bal.get)
    if bal[low] <= 1:
        items.append({"phase": "Ημέρες 1–30 · Θεμέλια", "text": M["west_elements"][low]["tip"]})
    items.append({"phase": "Ημέρες 31–60 · Χτίσιμο", "text": P["sun_practice"][sun["sign"]]})
    if chart["time_known"] and sat.get("house"):
        h = H[str(sat["house"])]
        items.append({"phase": "Ημέρες 31–60 · Χτίσιμο", "text": f"Δώσε 20 λεπτά την εβδομάδα, με υπομονή, σε ένα θέμα {h['where']}: ο Κρόνος σου εκεί επιβραβεύει τη σταθερή προσπάθεια."})
    else:
        items.append({"phase": "Ημέρες 31–60 · Χτίσιμο", "text": f"Διάλεξε ένα μικρό σχέδιο και δούλευέ το εβδομαδιαία: ο Κρόνος σου {S[sat['sign']]['in']} επιβραβεύει τη σταθερή προσπάθεια."})
    items.append({"phase": "Ημέρες 61–90 · Άνοιγμα", "text": P["personal_year"][str(n["personal_year"])]})
    C = lib("chinese")["elements"]
    cnt = ch["element_count"]; lowc = min(cnt, key=cnt.get)
    if cnt[lowc] == 0:
        items.append({"phase": "Ημέρες 61–90 · Άνοιγμα", "text": f"Για λίγη ισορροπία στο στοιχείο {C[lowc]['name']} (λείπει από τους πυλώνες σου): {C[lowc]['tip']}."})
    items.append({"phase": "Κάθε εβδομάδα", "text": "Κάθε Κυριακή γράψε 3 γραμμές: τι πήγε καλά, τι σε κούρασε, ποιο μικρό βήμα κάνεις την επόμενη εβδομάδα."})
    items.append({"phase": "Πάντα", "text": "Αν κάτι αφορά την υγεία σου, τα χρήματά σου, νομικά θέματα ή την ψυχική σου ασφάλεια, μίλησε με αρμόδιο επαγγελματία. Ο χάρτης είναι σύμβολο, όχι οδηγία."})
    return items


def generate(chart: dict, chinese: dict, numerology: dict, name: str | None = None) -> dict:
    tk = chart["time_known"]; P = chart["planets"]; S = lib("signs"); D = lib("misc")["disclaimers"]
    order = ["Sun", "Moon"] + (["Ascendant"] if tk else []) + ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "TrueNode", "Chiron"] + (["MC"] if tk else [])
    cards = []
    for k in order:
        if k == "Ascendant":
            cards.append(angle_card(k, chart["ascendant_pos"]))
        elif k == "MC":
            cards.append(angle_card(k, chart["mc_pos"]))
        elif k in P:
            cards.append(planet_card(k, P[k], tk))
    sun, moon = P["Sun"], P["Moon"]
    big3 = [f"Ήλιος {S[sun['sign']]['in']}: {S[sun['sign']]['keyword']}.", f"Σελήνη {S[moon['sign']]['in']}: {S[moon['sign']]['keyword']}."]
    if tk:
        asc = chart["ascendant_pos"]
        big3.append(f"Ωροσκόπος {S[asc['sign']]['in']}: {S[asc['sign']]['keyword']}.")
    greeting = f"{name.split()[0].capitalize()}, " if name and name.strip() else ""
    intro = (f"{greeting}ο χάρτης σου είναι σαν μια παλιά ζωγραφισμένη εικόνα του ουρανού τη στιγμή που ήρθες στον κόσμο. "
             "Δεν σου λέει τι θα συμβεί· σου δείχνει υλικά, ρυθμούς και ερωτήματα, και εσύ διαλέγεις τι θα κάνεις με αυτά. "
             "Διάβασέ τον σαν ιστορία: με περιέργεια, με ηρεμία και με ένα μικρό χαμόγελο.")
    notes = [D["short"]]
    if not tk:
        notes.append(D["no_time"])
        if chart.get("moon_sign_uncertain"):
            notes.append(D["moon_uncertain"])
    if chart.get("house_system") == "Porphyry":
        notes.append("Σε πολύ βόρεια γεωγραφικά πλάτη το σύστημα Placidus δεν ορίζεται· χρησιμοποιήθηκε το σύστημα Πορφυρίου για τους οίκους.")
    if "Chiron" not in P:
        notes.append("Ο Χείρων δεν υπολογίζεται για ημερομηνίες εκτός 1900–2100.")
    mp = lib("misc")["moon_phases"][chart["moon_phase"]["key"]]
    return {"intro": intro, "big_three": big3, "cards": cards, "aspects": aspects_text(chart),
            "balance": balance_text(chart),
            "moon_phase": {"name": mp["name"], "text": mp["text"], "illumination": chart["moon_phase"]["illumination"]},
            "chinese": chinese_text(chinese), "numerology": numerology_text(numerology),
            "ninety_days": ninety_days(chart, numerology, chinese), "notes": notes}
