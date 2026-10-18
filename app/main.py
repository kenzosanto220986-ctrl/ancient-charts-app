"""FastAPI app. Everything is in memory; nothing personal is written to disk or logged."""
from __future__ import annotations
import secrets, time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import service, chat
from .engine import geo, astro, transits
from .reading import lib

ROOT = Path(__file__).resolve().parent.parent
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_app):
    geo._index(); astro.eph(); astro._chiron_table(); transits._table(); transits._chiron_arrays()   # warm caches (city index ~2 s)
    yield


app = FastAPI(title="Αρχαίοι χάρτες — prototype", docs_url=None, redoc_url=None, lifespan=lifespan)

SESSIONS: dict[str, dict] = {}
TTL = 3 * 3600
MAX_SESSIONS = 300


def _purge():
    now = time.time()
    for k in [k for k, v in SESSIONS.items() if now - v["ts"] > TTL]:
        SESSIONS.pop(k, None)
    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.pop(min(SESSIONS, key=lambda k: SESSIONS[k]["ts"]))


class ChartIn(BaseModel):
    name: str | None = Field(None, max_length=80)
    date: str
    time: str | None = None
    time_unknown: bool = False
    city_id: str | None = None
    lat: float | None = None
    lon: float | None = None
    tz: str | None = None
    gender: str | None = None   # accepted but unused in this prototype (needed only for BaZi luck pillars)


class ChatIn(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=1200)


@app.get("/api/health")
def health():
    p = chat.provider()
    D = lib("misc")["disclaimers"]
    return {"ok": True, "llm": ({"provider": p["name"], "model": p["model"]} if p else None),
            "sessions": len(SESSIONS), "disclaimer_long": D["long"], "privacy": D["privacy"]}


@app.get("/api/cities")
def cities(q: str = Query(..., min_length=2, max_length=60)):
    return [{"id": str(c["id"]), "label": c["label"], "lat": c["lat"], "lon": c["lon"], "tz": c["tz"]} for c in geo.search_cities(q, 8)]


@app.get("/api/tz")
def tz_preview(city_id: str, date: str, time: str = "12:00"):
    """Timezone preview for the form (historical DST included)."""
    from datetime import datetime
    c = geo.get_city(city_id)
    if not c:
        raise HTTPException(404, "city")
    try:
        naive = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(400, "date")
    r = geo.resolve_local_time(c["tz"], naive)
    off = r["offset_hours"]; hh, mm = divmod(int(round(abs(off) * 60)), 60)
    return {"tz": c["tz"], "utc_offset": f"UTC{'+' if off >= 0 else '-'}{hh}" + (f":{mm:02d}" if mm else ""), "dst": r["dst"],
            "utc": r["utc"].strftime("%Y-%m-%d %H:%M"), "warnings": r["warnings"]}


@app.post("/api/chart")
def chart(inp: ChartIn):
    try:
        res = service.build(inp.model_dump())
    except service.InputError as e:
        raise HTTPException(400, str(e))
    _purge()
    sid = secrets.token_urlsafe(16)
    slim = {k: res[k] for k in ("input", "chart", "reading", "numerology", "time_known")}
    # keep sessions small (512 MB host): the big health tables (timeline, SVG) are not needed by the chat after the summary is built
    hh = res["reading"].get("health")
    if hh:
        slim["reading"] = {**res["reading"], "health": {"watch": [{"title": w["title"], "area": w["area"]} for w in hh["watch"]]}}
    SESSIONS[sid] = {"ts": time.time(), "res": slim, "summary": None, "history": []}
    SESSIONS[sid]["summary"] = chat.chart_summary(res)
    res["session_id"] = sid
    res["chat"] = {"llm": bool(chat.provider())}
    return JSONResponse(res)


@app.post("/api/chat")
def chat_api(inp: ChatIn):
    s = SESSIONS.get(inp.session_id)
    if not s or time.time() - s["ts"] > TTL:
        raise HTTPException(404, "Η συνεδρία έληξε. Υπολόγισε ξανά τον χάρτη σου.")
    s["ts"] = time.time()
    out = chat.answer(s["res"], s["summary"], s["history"], inp.message.strip())
    s["history"] += [{"role": "user", "content": inp.message.strip()}, {"role": "assistant", "content": out["reply"]}]
    s["history"] = s["history"][-24:]
    return out


@app.post("/api/forget")
def forget(body: dict):
    SESSIONS.pop(str(body.get("session_id", "")), None)
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
