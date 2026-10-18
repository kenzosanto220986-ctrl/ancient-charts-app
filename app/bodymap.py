"""Simple SVG body silhouette (the traditional «zodiac man») with one region per sign; highlighted signs get class «hl».
Pure markup, no user text inside (labels come from the Greek library), so it is safe to inject with innerHTML."""
from __future__ import annotations
from .reading import lib

GLYPH = {"Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋", "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
         "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓"}

# sign -> list of (svg shape markup, label x, label y); shapes are simple rounded forms around x = 110
ZONES = {
    "Aries": [('<ellipse cx="110" cy="36" rx="22" ry="27"/>', 110, 37)],
    "Taurus": [('<rect x="98" y="64" width="24" height="20" rx="8"/>', 110, 75)],
    "Gemini": [('<path d="M80 90 Q62 90 54 100 L36 188 Q34 198 40 204 L36 226 Q36 236 46 236 Q56 236 56 226 L62 204 L74 136 Z"/>', 56, 150),
               ('<path d="M140 90 Q158 90 166 100 L184 188 Q186 198 180 204 L184 226 Q184 236 174 236 Q164 236 164 226 L158 204 L146 136 Z"/>', 164, 150)],
    "Cancer": [('<rect x="80" y="88" width="60" height="32" rx="10"/>', 110, 105)],
    "Leo": [('<rect x="84" y="122" width="52" height="28" rx="8"/>', 110, 137)],
    "Virgo": [('<rect x="84" y="152" width="52" height="30" rx="8"/>', 110, 168)],
    "Libra": [('<rect x="82" y="184" width="56" height="26" rx="8"/>', 110, 198)],
    "Scorpio": [('<path d="M84 212 H136 L134 244 H86 Z"/>', 110, 229)],
    "Sagittarius": [('<path d="M86 246 H108 L106 318 H90 Z"/>', 97, 282), ('<path d="M112 246 H134 L130 318 H114 Z"/>', 123, 282)],
    "Capricorn": [('<ellipse cx="98" cy="334" rx="12" ry="14"/>', 98, 335), ('<ellipse cx="122" cy="334" rx="12" ry="14"/>', 122, 335)],
    "Aquarius": [('<path d="M88 352 H108 L106 414 H92 Z"/>', 98, 383), ('<path d="M112 352 H132 L128 414 H114 Z"/>', 122, 383)],
    "Pisces": [('<ellipse cx="94" cy="436" rx="17" ry="9"/>', 94, 437), ('<ellipse cx="126" cy="436" rx="17" ry="9"/>', 126, 437)],
}


def svg_bodymap(highlight: set[str] | None = None) -> str:
    highlight = highlight or set()
    S = lib("signs")
    parts = ['<svg class="bm" viewBox="0 0 220 460" role="img" aria-label="Χάρτης του σώματος ανά ζώδιο (συμβολικός)" xmlns="http://www.w3.org/2000/svg">']
    for sign, shapes in ZONES.items():
        hl = sign in highlight
        parts.append(f'<g class="zone{" hl" if hl else ""}" data-sign="{sign}"><title>{S[sign]["name"]}</title>')
        for shape, x, y in shapes:
            parts.append(shape.replace("/>", ' class="z"/>', 1))
        for shape, x, y in shapes:
            parts.append(f'<text class="bg" x="{x}" y="{y}">{GLYPH[sign]}</text>')
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts)
