"""
Database abstraction — supports PostgreSQL (production) and SQLite (local dev).
Set DATABASE_URL for Postgres; omit it to use SQLite at DB_PATH.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH      = os.getenv("DB_PATH", "./pramaana.db")

# Placeholder token differs between backends
PH = "%s" if DATABASE_URL else "?"


@contextmanager
def _conn():
    if DATABASE_URL:
        import psycopg2
        c = psycopg2.connect(DATABASE_URL)
        try:
            yield c
            c.commit()
        finally:
            c.close()
    else:
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()


def init_db() -> None:
    serial = "SERIAL" if DATABASE_URL else "INTEGER"
    with _conn() as c:
        cur = c.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS articles (
                share_id      TEXT PRIMARY KEY,
                url           TEXT NOT NULL,
                outlet        TEXT,
                region        TEXT,
                overall_score INTEGER,
                result_json   TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'pending',
                submitted_by  TEXT,
                submitted_at  TEXT NOT NULL,
                approved_at   TEXT,
                approved_by   TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_status  ON articles(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_outlet  ON articles(outlet)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_region  ON articles(region)")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS usage (
                id         {serial} PRIMARY KEY,
                ip         TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_created ON usage(created_at)")


# ── Article CRUD ──────────────────────────────────────────────────────────────

def upsert_article(share_id: str, url: str, result: dict,
                   status: str = "pending", submitted_by: str = "") -> None:
    """Insert or replace an article. Seed articles use status='approved'."""
    now    = datetime.now(timezone.utc).isoformat()
    outlet = (result.get("outlet") or "").strip()
    region = result.get("region", "")
    score  = result.get("overall_score")
    rjson  = json.dumps(result)

    with _conn() as c:
        cur = c.cursor()
        if DATABASE_URL:
            cur.execute(f"""
                INSERT INTO articles
                    (share_id, url, outlet, region, overall_score,
                     result_json, status, submitted_by, submitted_at)
                VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
                ON CONFLICT (share_id) DO UPDATE SET
                    outlet        = EXCLUDED.outlet,
                    region        = EXCLUDED.region,
                    overall_score = EXCLUDED.overall_score,
                    result_json   = EXCLUDED.result_json,
                    status        = EXCLUDED.status,
                    submitted_by  = EXCLUDED.submitted_by,
                    submitted_at  = EXCLUDED.submitted_at
            """, (share_id, url, outlet, region, score, rjson,
                  status, submitted_by, now))
        else:
            cur.execute(f"""
                INSERT OR REPLACE INTO articles
                    (share_id, url, outlet, region, overall_score,
                     result_json, status, submitted_by, submitted_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (share_id, url, outlet, region, score, rjson,
                  status, submitted_by, now))


def get_article(share_id: str) -> Optional[dict]:
    with _conn() as c:
        cur = c.cursor()
        cur.execute(f"SELECT result_json FROM articles WHERE share_id={PH}", (share_id,))
        row = cur.fetchone()
    return json.loads(row[0]) if row else None


def get_pending() -> list[dict]:
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT share_id, url, outlet, region, overall_score, result_json, submitted_at
            FROM articles WHERE status='pending'
            ORDER BY submitted_at DESC
        """)
        rows = cur.fetchall()
    return [
        {
            "share_id":     r[0],
            "url":          r[1],
            "outlet":       r[2] or "",
            "region":       r[3] or "",
            "overall_score": r[4],
            "result_json":  json.loads(r[5]),
            "submitted_at": r[6],
        }
        for r in rows
    ]


def get_history(limit: int = 50) -> list[dict]:
    with _conn() as c:
        cur = c.cursor()
        cur.execute(f"""
            SELECT share_id, url, outlet, region, overall_score,
                   result_json, status, approved_at, approved_by
            FROM articles
            WHERE status IN ('approved','rejected')
            ORDER BY approved_at DESC
            LIMIT {limit}
        """)
        rows = cur.fetchall()
    return [
        {
            "share_id":      r[0],
            "url":           r[1],
            "outlet":        r[2] or "",
            "region":        r[3] or "",
            "overall_score": r[4],
            "title":         json.loads(r[5]).get("article_title", r[1]),
            "status":        r[6],
            "approved_at":   r[7] or "",
            "approved_by":   r[8] or "",
        }
        for r in rows
    ]


def approve_article(share_id: str, outlet: str, region: str,
                    approved_by: str = "admin") -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.cursor()
        cur.execute(f"""
            UPDATE articles
            SET status={PH}, outlet={PH}, region={PH},
                approved_at={PH}, approved_by={PH}
            WHERE share_id={PH}
        """, ("approved", outlet.strip(), region, now, approved_by, share_id))
        return (cur.rowcount or 0) > 0


def reject_article(share_id: str) -> bool:
    with _conn() as c:
        cur = c.cursor()
        cur.execute(f"UPDATE articles SET status={PH} WHERE share_id={PH}",
                    ("rejected", share_id))
        return (cur.rowcount or 0) > 0


# ── Leaderboard ───────────────────────────────────────────────────────────────

_DIM_ORDER = ["Source trust", "Claim verifiability",
              "Cross-source consensus", "Narrative transparency",
              "Contextual completeness"]


def get_leaderboard() -> list[dict]:
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT outlet, overall_score, result_json
            FROM articles
            WHERE status='approved' AND region='india'
              AND outlet IS NOT NULL AND outlet != '' AND outlet != 'Unknown'
              AND overall_score IS NOT NULL
        """)
        rows = cur.fetchall()

    outlet_map: dict = {}
    for row in rows:
        outlet, score, rjson = row[0], row[1], row[2]
        r = json.loads(rjson)
        if outlet not in outlet_map:
            outlet_map[outlet] = {"scores": [], "dims": {}}
        outlet_map[outlet]["scores"].append(int(score))
        for dim in (r.get("dimensions") or []):
            name = (dim.get("name") or "").strip()
            ds   = dim.get("score")
            if name and isinstance(ds, (int, float)):
                outlet_map[outlet]["dims"].setdefault(name, []).append(int(ds))

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


# ── Rate limiting ─────────────────────────────────────────────────────────────

IP_LIMIT     = int(os.getenv("PRAMAANA_IP_LIMIT", "5"))
GLOBAL_LIMIT = int(os.getenv("PRAMAANA_GLOBAL_LIMIT", "100"))


def check_limits(ip: str) -> tuple:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    with _conn() as c:
        cur = c.cursor()
        cur.execute(f"SELECT COUNT(*) FROM usage WHERE created_at>{PH}", (cutoff,))
        global_count = cur.fetchone()[0]
        if global_count >= GLOBAL_LIMIT:
            return False, (
                "Pramaana is at daily capacity. Browse pre-analyzed articles below, "
                "or self-host with your own API key — see the README."
            )
        cur.execute(f"SELECT COUNT(*) FROM usage WHERE ip={PH} AND created_at>{PH}",
                    (ip, cutoff))
        ip_count = cur.fetchone()[0]
        if ip_count >= IP_LIMIT:
            return False, (
                f"You've used your {IP_LIMIT} free analyses for today. "
                "Self-host with your own API key for unlimited access — see the README."
            )
    return True, ""


def record_usage(ip: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.cursor()
        cur.execute(f"INSERT INTO usage (ip, created_at) VALUES ({PH},{PH})", (ip, now))
