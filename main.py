import asyncio
import hashlib
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import db
from pramaana_data import PRAMAANA_SEED

BASE_DIR    = Path(__file__).parent
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

app = FastAPI(title="Pramaana", description="Structural article credibility analysis")

# Hot-path result cache: share_id → result dict
_cache: dict = {}


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    db.init_db()
    _seed()


def _seed() -> None:
    """Seed the DB with curated founding articles (always approved)."""
    for item in PRAMAANA_SEED:
        url      = item.get("source_url", "")
        share_id = hashlib.md5(url.encode()).hexdigest()
        db.upsert_article(share_id, url, item, status="approved", submitted_by="seed")


# ── Claude API ────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are Pramaana, an expert media credibility analyst specializing in South Asian and global geopolitical news. You analyze articles with deep knowledge of Indian, Pakistani, Bangladeshi, Chinese, and Western media ecosystems — their ownership structures, political alignments, funding sources, and narrative patterns.

You return ONLY a valid JSON object — no markdown, no preamble, no explanation outside the JSON. The JSON must exactly match this schema:
{
  "article_title": "string",
  "source_url": "string",
  "outlet": "string — canonical outlet name",
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


def _call_claude(url: str, api_key: str) -> dict:
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


# ── Auth helper ───────────────────────────────────────────────────────────────

def _require_admin(request: Request) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(500, "ADMIN_TOKEN not configured")
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(401, "Unauthorized")


# ── Public routes ─────────────────────────────────────────────────────────────

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
async def get_result(share_id: str):
    if share_id in _cache:
        return JSONResponse({**_cache[share_id], "share_id": share_id})
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, db.get_article, share_id)
    if not result:
        raise HTTPException(404, "Result not found")
    _cache[share_id] = result
    return JSONResponse({**result, "share_id": share_id})


@app.get("/api/pramaana/leaderboard")
async def leaderboard():
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, db.get_leaderboard)
    return JSONResponse(data)


@app.post("/api/pramaana/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    url = req.url.strip()
    if not url:
        raise HTTPException(400, "url is required")
    share_id = hashlib.md5(url.encode()).hexdigest()

    # 1. Memory cache
    if share_id in _cache:
        return JSONResponse({**_cache[share_id], "share_id": share_id})

    # 2. DB (covers previously analyzed + seed articles)
    loop   = asyncio.get_event_loop()
    stored = await loop.run_in_executor(None, db.get_article, share_id)
    if stored:
        _cache[share_id] = stored
        return JSONResponse({**stored, "share_id": share_id})

    # 3. Fresh analysis — rate limited
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "unknown"))
    allowed, msg = await loop.run_in_executor(None, db.check_limits, ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY not configured")

    result = await loop.run_in_executor(None, _call_claude, url, api_key)
    _cache[share_id] = result
    await loop.run_in_executor(None, db.upsert_article,
                               share_id, url, result, "pending", ip)
    await loop.run_in_executor(None, db.record_usage, ip)
    return JSONResponse({**result, "share_id": share_id})


# ── Admin routes ──────────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    return HTMLResponse(content=(BASE_DIR / "admin.html").read_text(encoding="utf-8"))


@app.get("/api/admin/pending")
async def admin_pending(request: Request):
    _require_admin(request)
    loop = asyncio.get_event_loop()
    rows = await loop.run_in_executor(None, db.get_pending)
    return JSONResponse(rows)


@app.post("/api/admin/approve/{share_id}")
async def admin_approve(share_id: str, request: Request):
    _require_admin(request)
    body   = await request.json()
    outlet = (body.get("outlet") or "").strip()
    region = body.get("region", "india")
    if not outlet:
        raise HTTPException(400, "outlet is required")
    loop = asyncio.get_event_loop()
    ok   = await loop.run_in_executor(None, db.approve_article, share_id, outlet, region)
    if not ok:
        raise HTTPException(404, "Article not found")
    # evict from cache so leaderboard picks up new outlet/region
    _cache.pop(share_id, None)
    return JSONResponse({"status": "approved"})


@app.post("/api/admin/reject/{share_id}")
async def admin_reject(share_id: str, request: Request):
    _require_admin(request)
    loop = asyncio.get_event_loop()
    ok   = await loop.run_in_executor(None, db.reject_article, share_id)
    if not ok:
        raise HTTPException(404, "Article not found")
    return JSONResponse({"status": "rejected"})
