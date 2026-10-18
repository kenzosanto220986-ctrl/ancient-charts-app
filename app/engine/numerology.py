"""Pythagorean numerology (Latin letters A-Z; Greek letters are transliterated). Master numbers 11, 22, 33 are kept."""
from __future__ import annotations
import re, unicodedata
from datetime import date

PYTH = {c: (i % 9) + 1 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
GREEK = {"α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
         "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y", "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o"}
MASTER = (11, 22, 33)


def reduce_num(n: int, keep_master=True) -> int:
    while n > 9 and not (keep_master and n in MASTER):
        n = sum(int(c) for c in str(n))
    return n


def normalize_name(name: str) -> str:
    """Strip accents, transliterate Greek, keep A-Z and spaces."""
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    for a, b in (("ου", "ou"), ("αυ", "av"), ("ευ", "ev"), ("μπ", "b"), ("ντ", "d"), ("γκ", "g"), ("γγ", "ng")):
        s = s.replace(a, b)
    s = "".join(GREEK.get(c, c) for c in s)
    s = re.sub(r"[^a-z ]", "", s)
    return re.sub(r"\s+", " ", s).strip().upper()


def _letters(name: str):
    """Yield (letter, is_vowel). Y is a vowel only when no neighbouring letter in the word is a vowel."""
    for word in name.split():
        for i, ch in enumerate(word):
            if ch in "AEIOU":
                v = True
            elif ch == "Y":
                prev = word[i - 1] if i > 0 else ""
                nxt = word[i + 1] if i + 1 < len(word) else ""
                v = prev not in tuple("AEIOU") and nxt not in tuple("AEIOU")
            else:
                v = False
            yield ch, v


def life_path(y: int, m: int, d: int) -> int:
    return reduce_num(reduce_num(m) + reduce_num(d) + reduce_num(y))


def compute(year: int, month: int, day: int, name: str | None = None, today: date | None = None):
    today = today or date.today()
    out = {"life_path": life_path(year, month, day), "birthday": reduce_num(day)}
    out["birthday_raw"] = day
    # personal year (traditional 1-9): day + month + current calendar year
    py = day + month + sum(int(c) for c in str(today.year))
    out["personal_year"] = reduce_num(py, keep_master=False)
    out["personal_year_for"] = today.year
    nm = normalize_name(name) if name else ""
    out["name_used"] = nm or None
    if nm:
        letters = list(_letters(nm))
        tot = sum(PYTH[c] for c, _ in letters)
        soul = sum(PYTH[c] for c, v in letters if v)
        pers = sum(PYTH[c] for c, v in letters if not v)
        if tot > 0:
            out["destiny"] = reduce_num(tot)
            out["maturity"] = reduce_num(out["life_path"] + out["destiny"])
        if soul > 0:
            out["soul"] = reduce_num(soul)
        if pers > 0:
            out["personality"] = reduce_num(pers)
    return out
