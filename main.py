import asyncio
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from pramaana_data import PRAMAANA_SEED

BASE_DIR = Path(__file__).parent
DB_PATH  = os.getenv("DB_PATH", str(BASE_DIR / "pramaana.db"))

app = FastAPI(title="Pramaana", description="Article credibility analysis API")

# ── In-memory result cache (URL md5 → result dict) ───────────────────────────
_cache: dict = {}

# ── Rate limiting ─────────────────────────────────────────────────────────────
IP_LIMIT     = int(os.getenv("PRAMAANA_IP_LIMIT", "5"))       # analyses / IP / 24h
GLOBAL_LIMIT = int(os.getenv("PRAMAANA_GLOBAL_LIMIT", "100")) # total analyses / 24h


# ── Database ──────────────────────────────────────────────────────────────────
def init_db() -> None:
    with sqlite3.connect(DB_PATH) as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS pramaana_results (
                share_id   TEXT PRIMARY KEY,
                url        TEXT NOT NULL,
                result     TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pramaana_usage (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ip         TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_usage_created ON pramaana_usage(created_at);
        """)


def save_result(share_id: str, url: str, result: dict) -> None:
    with sqlite3.connect(DB_PATH) as c:
        c.execute(
            "INSERT OR REPLACE INTO pramaana_results (share_id, url, result, created_at) VALUES (?,?,?,?)",
            (share_id, url, json.dumps(result), datetime.now(timezone.utc).isoformat()),
        )
        c.commit()


def get_result(share_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute(
            "SELECT result FROM pramaana_results WHERE share_id=?", (share_id,)
        ).fetchone()
    return json.loads(row[0]) if row else None


def check_limits(ip: str) -> tuple[bool, str]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    with sqlite3.connect(DB_PATH) as c:
        global_count = c.execute(
            "SELECT COUNT(*) FROM pramaana_usage WHERE created_at > ?", (cutoff,)
        ).fetchone()[0]
        if global_count >= GLOBAL_LIMIT:
            return False, (
                "Pramaana is at daily capacity. Browse pre-analyzed articles below, "
                "or self-host with your own API key — see the README."
            )
        ip_count = c.execute(
            "SELECT COUNT(*) FROM pramaana_usage WHERE ip=? AND created_at > ?",
            (ip, cutoff),
        ).fetchone()[0]
        if ip_count >= IP_LIMIT:
            return False, (
                f"You've used your {IP_LIMIT} free analyses for today. "
                "Self-host with your own API key for unlimited access — see the README."
            )
    return True, ""


def record_usage(ip: str) -> None:
    with sqlite3.connect(DB_PATH) as c:
        c.execute(
            "INSERT INTO pramaana_usage (ip, created_at) VALUES (?,?)",
            (ip, datetime.now(timezone.utc).isoformat()),
        )
        c.commit()


def seed_results() -> None:
    with sqlite3.connect(DB_PATH) as c:
        for item in PRAMAANA_SEED:
            url      = item.get("source_url", "")
            share_id = hashlib.md5(url.encode()).hexdigest()
            c.execute(
                "INSERT OR REPLACE INTO pramaana_results (share_id, url, result, created_at) VALUES (?,?,?,?)",
                (share_id, url, json.dumps(item), datetime.now(timezone.utc).isoformat()),
            )
        c.commit()


# ── Claude API call ───────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are Pramaana, an expert media credibility analyst specializing in South Asian and global geopolitical news. You analyze articles with deep knowledge of Indian, Pakistani, Bangladeshi, Chinese, and Western media ecosystems — their ownership structures, political alignments, funding sources, and narrative patterns.

You return ONLY a valid JSON object — no markdown, no preamble, no explanation outside the JSON. The JSON must exactly match this schema:
{
  "article_title": "string",
  "source_url": "string",
  "outlet": "string",
  "overall_score": number (0-100),
  "verdict": "string — 2-3 sentences, sharp and editorial",
  "dimensions": [
    { "name": "Source trust", "score": number, "note": "max 8 words" },
    { "name": "Claim verifiability", "score": number, "note": "max 8 words" },
    { "name": "Cross-source consensus", "score": number, "note": "max 8 words" },
    { "name": "Narrative transparency", "score": number, "note": "max 8 words" },
    { "name": "Contextual completeness", "score": number, "note": "max 8 words" }
  ],
  "source_funding": "string — 2-3 sentences",
  "claims": [{ "type": "fact|opinion|contested|unverifiable", "text": "string" }],
  "cross_source": [{ "outlet": "string", "stance": "agree|partial|diverge|silent", "note": "string" }],
  "narrative_beneficiary": "string — 2 sentences, name specific actors",
  "missing_context": ["string", "string", "string"]
}
Rules: exactly 4 claims, 4 cross_source entries, 3 missing_context items. Score 70-100 credible, 40-69 mixed, 0-39 low."""


def call_claude(url: str, api_key: str) -> dict:
    import anthropic
    client  = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": (
            f"Analyze credibility of: {url}\n"
            "Analyze based on outlet ownership, funding, editorial history, "
            "coverage patterns, and cross-source comparison. Return JSON only."
        )}],
    )
    raw = message.content[0].text
    return json.loads(raw[raw.find("{"):raw.rfind("}")+1])


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    init_db()
    seed_results()


# ── Routes ────────────────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    url: str


@app.get("/", response_class=HTMLResponse)
@app.get("/pramaana", response_class=HTMLResponse)
async def serve_ui():
    return HTMLResponse(content=(BASE_DIR / "pramaana.html").read_text(encoding="utf-8"))


@app.get("/api/pramaana/showcase")
async def showcase():
    items = []
    for item in PRAMAANA_SEED:
        share_id = hashlib.md5(item.get("source_url", "").encode()).hexdigest()
        items.append({**item, "share_id": share_id})
    return JSONResponse(items)


@app.get("/api/pramaana/result/{share_id}")
async def get_result_route(share_id: str):
    if share_id in _cache:
        return JSONResponse({**_cache[share_id], "share_id": share_id})
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_result, share_id)
    if not result:
        raise HTTPException(404, "Result not found")
    _cache[share_id] = result
    return JSONResponse({**result, "share_id": share_id})


@app.get("/api/pramaana/leaderboard")
async def leaderboard():
    loop = asyncio.get_event_loop()

    def _fetch():
        with sqlite3.connect(DB_PATH) as c:
            rows = c.execute("SELECT result FROM pramaana_results").fetchall()
        outlet_map: dict = {}
        for row in rows:
            try:
                r = json.loads(row[0])
            except Exception:
                continue
            outlet = (r.get("outlet") or "").strip()
            score  = r.get("overall_score")
            region = r.get("region", "")
            if not outlet or outlet.lower() == "unknown":
                continue
            if region != "india":
                continue
            if not isinstance(score, (int, float)):
                continue
            if outlet not in outlet_map:
                outlet_map[outlet] = {"scores": [], "dims": {}}
            outlet_map[outlet]["scores"].append(int(score))
            for dim in (r.get("dimensions") or []):
                name = dim.get("name", "").strip()
                ds   = dim.get("score")
                if name and isinstance(ds, (int, float)):
                    outlet_map[outlet]["dims"].setdefault(name, []).append(int(ds))

        _DIM_ORDER = ["Source trust", "Claim verifiability",
                      "Cross-source consensus", "Narrative transparency",
                      "Contextual completeness"]
        result = []
        for outlet, data in outlet_map.items():
            scores = data["scores"]
            dims   = [
                {"name": n, "avg": round(sum(v) / len(v))}
                for n, v in data["dims"].items()
            ]
            dims.sort(key=lambda x: _DIM_ORDER.index(x["name"])
                      if x["name"] in _DIM_ORDER else 99)
            result.append({
                "outlet":     outlet,
                "avg_score":  round(sum(scores) / len(scores)),
                "articles":   len(scores),
                "dimensions": dims,
            })
        result.sort(key=lambda x: x["avg_score"], reverse=True)
        return result

    return JSONResponse(await loop.run_in_executor(None, _fetch))


@app.post("/api/pramaana/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    url = req.url.strip()
    if not url:
        raise HTTPException(400, "url is required")
    share_id = hashlib.md5(url.encode()).hexdigest()

    if share_id in _cache:
        return JSONResponse({**_cache[share_id], "share_id": share_id})

    loop   = asyncio.get_event_loop()
    stored = await loop.run_in_executor(None, get_result, share_id)
    if stored:
        _cache[share_id] = stored
        return JSONResponse({**stored, "share_id": share_id})

    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "unknown"))
    allowed, msg = await loop.run_in_executor(None, check_limits, ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY not configured — see README for self-hosting")

    result = await loop.run_in_executor(None, call_claude, url, api_key)
    _cache[share_id] = result
    await loop.run_in_executor(None, save_result, share_id, url, result)
    await loop.run_in_executor(None, record_usage, ip)
    return JSONResponse({**result, "share_id": share_id})
