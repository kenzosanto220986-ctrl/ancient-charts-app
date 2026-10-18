# Αρχαίοι χάρτες — companion app (prototype)

Greek-language web app: enter birth date / time / place → natal chart (SVG wheel) + simple, storytelling Greek reading
+ Chinese Four Pillars + Pythagorean numerology + **symbolic medical astrology («Υγεία (συμβολική)»)** + 90-day suggestions + a chat guide for daily questions.
**Prototype**: in-memory only, local only, no accounts, no database, not deployed anywhere.

Everything shown is labelled *symbolic* (not medical / legal / financial advice).

## Run

```bash
cd /workspace/astro_app
./start.sh            # creates .venv on first run, serves http://127.0.0.1:8765   (./start.sh 9000 for another port)
```

Open <http://127.0.0.1:8765>. Click **«Δείγμα (φανταστικό πρόσωπο)»** to fill in a fictional sample person.

Requirements: Python 3.11+ (tested on 3.13), internet only for the first `pip install`. The ephemeris (`app/data/de421.bsp`,
JPL DE421, 1899–2053), the Chiron table (`app/data/chiron.csv`), city list (geonamescache), tz database (tzdata) and fonts
(`static/fonts`, Noto, self-hosted) all ship locally — no third-party requests at runtime.

## Tests

```bash
.venv/bin/python -m pytest -q tests        # 54 tests, ~9 s
```

`tests/test_health.py` (fictional people only) covers the health section: structure, disclaimers and forbidden wording, body map, watch points, element imbalance, no-birth-time case, real Saturn/Jupiter/nodal/Uranus/Chiron ages checked against the ephemeris, next-10-years calendar, edge birth years (1900, 2040, 2050), speed/memory, Chinese layer, API + chat awareness.

The regression suite includes the owner-supplied regression chart (Sun, Moon, Ascendant, MC, four pillars, Life Path – values live only in
`tests/`, never in the app/UI), a Houston 1974 "does not crash" check, historical-DST checks (zoneinfo vs pytz),
Lichun boundary, master numbers, unknown birth time, polar latitudes, API flow, chat safety and the LLM adapter.

## Chat / LLM

The chat sends *user message + compact chart summary + system prompt* to any OpenAI-compatible `/chat/completions` endpoint.
Configure with environment variables before `./start.sh` (first match wins):

| Variable | Meaning |
|---|---|
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | generic OpenAI-compatible endpoint |
| `XAI_API_KEY` | xAI (`https://api.x.ai/v1`, default model `grok-4`, override with `LLM_MODEL`) |
| `OPENAI_API_KEY` | OpenAI (`https://api.openai.com/v1`, default `gpt-4o-mini`) |

**No key is set in this environment**, so the chat currently runs the **local fallback**: it detects the topic
(love, work, money, health, feelings, decision, today, self, year), answers from the Greek text library + today's Moon sign,
adds the stoic frame, and asks one short follow-up. The UI shows a yellow "local mode" banner (green when an LLM is connected).
If the LLM call fails the app degrades to the local fallback and says so.

Safety is enforced **before** the LLM is called: crisis keywords (self-harm etc.) → fixed Greek reply with 112 / 1018;
urgent-medical keywords → 112. Money/health/legal topics get an explicit "not advice, see a professional" line.
The system prompt is `SYSTEM_PROMPT` in `app/chat.py` (Greek, stoic, practical, symbolic only, short answers + one question, remembers the chart).

## What is computed

* Skyfield + JPL DE421: Sun…Pluto (apparent, tropical, ecliptic of date), retrograde flags, **True Node** (osculating, from the Moon's state vector),
  **Chiron** (JPL Horizons table 1900–2100, 5-day step, cubic Hermite interpolation; regenerate with `tools/build_chiron_table.py`),
  Ascendant, MC (true obliquity, apparent sidereal time), 12 **Placidus** cusps (Porphyry fallback above 66° latitude).
* Aspects: conjunction/sextile/square/trine/opposition, orbs 8/5/7/7/8 (+1 for luminaries, −2 for nodes/Chiron/angles), "tight" < 3°, applying/separating.
* Element / modality balance, moon phase (8 phases + illumination).
* Time zone: city (geonamescache, ~69k cities, Greek names searchable) → IANA zone → `zoneinfo`/tzdata historical rules (e.g. Tbilisi 22 Sep 1986 = UTC+5 summer time);
  DST gaps/overlaps and LMT/old-date cases are flagged in the UI.
* Chinese Four Pillars: year/month from real solar terms (Lichun 315° boundary), day from JDN, hour for **clock** time and **true solar time**
  (longitude + equation of time); day changes at 23:00 (documented). Five-element count, Day Master.
* Numerology (Pythagorean, Latin letters; Greek names are transliterated): Life Path, Destiny, Soul, Personality, Birthday, Maturity (11/22/33 kept), Personal Year (1–9).

## Symbolic medical astrology («Ιατρική αστρολογία (συμβολική)»)

A tab «Υγεία (συμβολική)» in the results page (`reading.health` in `/api/chart`). **Symbolic guidance only**: no diagnosis, no prediction of illness
(wording is «τάση» / «ευαίσθητο σημείο», never «θα αρρωστήσεις»), no supplements/dosages/treatments, a disclaimer at the top **and** the bottom, an honest line
that there is no scientific evidence that astrology predicts health, and a reminder for regular check-ups and a doctor for any symptom. Texts live in `app/library/health.json`,
the assembler is `app/health.py` (same «library + assembler» pattern as `reading.py`), the SVG body map is `app/bodymap.py`.

1. **Body map** – 12 signs → body areas (Aries head/brain/eyes … Pisces feet/lymph) and 11 planets → systems (Sun heart/vitality/spine, Moon stomach/fluids/rhythm … Chiron sensitive points).
   Simple SVG «zodiac man»; signs that carry the Ascendant, Sun, Moon, 6th-house cusp and Chiron of *this* chart are highlighted (tap a region to open its text).
2. **Σημεία προσοχής** (computed from the chart, each with area · tendency · tightness · a gentle lifestyle step): Ascendant sign + its ruler, Sun sign, Moon sign, 6th/8th/12th house
   (sign on the cusp + planets inside + ruler of the 6th), hard natal aspects (conjunction/square/opposition, orb ≤ 5°, labelled very tight < 1° / tight < 3° / medium / wider) between
   Saturn, Mars, Pluto, Neptune or Uranus and any planet/Ascendant, element excess/lack (fire → burnout/inflammation/stress, no earth → grounding/sleep/digestion, …), Chiron sign + house.
   Modern rulers are used (Scorpio Pluto, Aquarius Uranus, Pisces Neptune). **Unknown birth time:** Ascendant, houses and Moon aspects are skipped and the UI says so.
3. **Age timeline 0–90** (`app/engine/transits.py`, numpy-vectorised, ~0.4 s and < 15 MB per chart): real transit windows of Saturn, Uranus, Neptune, Pluto and Chiron making conjunction/square/opposition
   to natal Sun, Moon, Ascendant, Saturn, the 6th-house cusp and the 6th-house ruler (orb 2° Saturn, 1.5° the others, retrograde passes merged, exact dates listed), slow planets crossing the 6th house,
   plus milestones: Saturn return/squares/opposition to natal Saturn (~7, 14, 22, 29, 36, 44, 51, 59…), Uranus square/opposition/return, Neptune square, Chiron return, Jupiter returns, nodal returns (~18.6 y),
   secondary-progression milestones (progressed Sun sign change, progressed new/full Moon, progressed Moon return) and the next lunar return. Shown as a table by age band
   (0–14, 15–29, 30–44, 45–59, 60–74, 75+; milestones always, up to 7 strongest ordinary windows per band) with a «τι να προσέξεις» column (cards on mobile),
   and the **next 10 years in full detail with calendar years** (a year strip + every window).
   Slow-planet longitudes come from `app/data/transit_table.npz` (1.5 MB: Jupiter…Pluto, 2-day grid 1900–2150 from JPL DE440s, linear interpolation, < 0.002° vs DE421 — see `tools/build_transit_table.py`),
   so DE421's 2053 limit does not cut the timeline and the 32 MB kernel does not ship; Chiron uses the existing Horizons table (so Chiron windows stop in 2100). With unknown birth time the timeline keeps only Sun/Saturn/outer-planet items.
4. **Chinese medicine layer** – five-element counts from the BaZi pillars (wood liver/gallbladder, fire heart/small intestine, earth spleen/stomach, metal lungs/large intestine, water kidneys/bladder):
   strong / balanced / light / missing + what to watch, and a short health theme for the Life Path, Destiny and Personal-Year numbers.

The chat guide knows the section: the chart summary sent to the LLM contains the watch points, the next-10-years windows and the Chinese element balance, plus explicit guardrails
(`SYSTEM_PROMPT`); the local fallback points to the tab and repeats the disclaimer. Sessions keep only a slim copy of the health data (memory).

Reading library = JSON in `app/library/` (`planets, signs (12×12 mode sentences), houses, aspects, chinese (12 animals, 5 elements, 10 day-master stems), numbers (1–9, 11, 22, 33), misc, health`).
Edit the Greek there; `app/reading.py` only assembles it (4-step pattern per planet: what it is → how it works in the sign → where in life (house) → one-line summary).

## Layout

```
start.sh  requirements.txt  README.md
app/main.py        FastAPI (API + static), in-memory sessions (3 h TTL)
app/service.py     input → tz → chart + pillars + numerology + reading + SVG
app/engine/        astro.py  chinese.py  numerology.py  geo.py
app/reading.py     Greek reading assembler        app/wheel.py  SVG natal wheel
app/health.py      symbolic medical astrology      app/bodymap.py  SVG body map      app/engine/transits.py  age-timeline engine
app/chat.py        LLM adapter + local fallback + safety
app/library/*.json Greek text library             app/data/  de421.bsp, chiron.csv, transit_table.npz
static/            index.html  app.js  style.css  fonts/   (navy / gold / silver, Noto, mobile-friendly)
tests/  tools/  screenshots/
```

API: `GET /api/cities?q=` · `GET /api/tz?city_id&date&time` · `POST /api/chart` · `POST /api/chat` · `POST /api/forget` · `GET /api/health`.

## Privacy

Nothing is written to disk (a test checks this); charts and chat history live in server memory for ≤ 3 h and vanish on restart; the server is started with
`--no-access-log` so city searches are not logged; the server binds to `127.0.0.1` only. If an external LLM is configured, the chart summary and chat messages go to that provider (stated in the UI).
Birth data are never in the repo: the sample button uses a fictional person.

## Known limits

Date range 1900–2050 (DE421). Chiron needs 1900–2100. Pre-1970 tzdata may be coarse; Placidus undefined above ~66° latitude.
Gender is accepted by the API but unused (needed only for BaZi luck pillars). No forecasts: the only transit calculation is the symbolic age timeline of the health tab (slow planets only, Chiron until 2100, days-level accuracy). Greek text is a first draft and should get a native-speaker/editor pass (especially `app/library/health.json`).
