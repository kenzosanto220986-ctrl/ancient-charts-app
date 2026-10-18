# Αρχαίοι χάρτες — companion app (prototype)

Greek-language web app: enter birth date / time / place → natal chart (SVG wheel) + simple, storytelling Greek reading
+ Chinese Four Pillars + Pythagorean numerology + 90-day suggestions + a chat guide for daily questions.
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
.venv/bin/python -m pytest -q tests        # 28 tests, ~3 s
```

Includes the owner-supplied regression chart (Sun, Moon, Ascendant, MC, four pillars, Life Path – values live only in
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

Reading library = JSON in `app/library/` (`planets, signs (12×12 mode sentences), houses, aspects, chinese (12 animals, 5 elements, 10 day-master stems), numbers (1–9, 11, 22, 33), misc`).
Edit the Greek there; `app/reading.py` only assembles it (4-step pattern per planet: what it is → how it works in the sign → where in life (house) → one-line summary).

## Layout

```
start.sh  requirements.txt  README.md
app/main.py        FastAPI (API + static), in-memory sessions (3 h TTL)
app/service.py     input → tz → chart + pillars + numerology + reading + SVG
app/engine/        astro.py  chinese.py  numerology.py  geo.py
app/reading.py     Greek reading assembler        app/wheel.py  SVG natal wheel
app/chat.py        LLM adapter + local fallback + safety
app/library/*.json Greek text library             app/data/  de421.bsp, chiron.csv
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
Gender is accepted by the API but unused (needed only for BaZi luck pillars). No transits / forecasts. Greek text is a first draft and should get a native-speaker/editor pass.
