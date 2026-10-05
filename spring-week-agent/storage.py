"""Small SQLite persistence layer for scan results and user configuration."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "data" / "spring_finder.sqlite3"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript("""
      CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL, message TEXT);
      CREATE TABLE IF NOT EXISTS opportunities (id INTEGER PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, data TEXT NOT NULL, first_seen TEXT NOT NULL, scan_id INTEGER);
      CREATE TABLE IF NOT EXISTS insights (id INTEGER PRIMARY KEY, opportunity_fingerprint TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """)
    return db


def save_setting(key: str, value: Any) -> None:
    with connect() as db:
        db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))


def get_setting(key: str, default: Any = None) -> Any:
    with connect() as db:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default


def add_scan(created_at: str, status: str, message: str = "") -> int:
    with connect() as db:
        cur = db.execute("INSERT INTO scans(created_at,status,message) VALUES(?,?,?)", (created_at, status, message))
        return int(cur.lastrowid)


def save_opportunity(item: dict[str, Any], scan_id: int, created_at: str) -> bool:
    import hashlib
    key = "|".join(str(item.get(k, "")).lower().strip() for k in ("company_name", "program_title", "direct_application_url"))
    fingerprint = hashlib.sha256(key.encode()).hexdigest()
    with connect() as db:
        cur = db.execute("INSERT OR IGNORE INTO opportunities(fingerprint,data,first_seen,scan_id) VALUES(?,?,?,?)", (fingerprint, json.dumps(item), created_at, scan_id))
        return cur.rowcount > 0


def save_insights(fingerprint: str, items: list[dict[str, Any]], created_at: str) -> None:
    with connect() as db:
        db.executemany("INSERT INTO insights(opportunity_fingerprint,data,created_at) VALUES(?,?,?)", [(fingerprint, json.dumps(x), created_at) for x in items])


def list_opportunities() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT data,first_seen FROM opportunities ORDER BY first_seen DESC").fetchall()
        return [{**json.loads(row[0]), "first_seen": row[1]} for row in rows]


def list_insights() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT data,created_at FROM insights ORDER BY created_at DESC").fetchall()
        return [{**json.loads(row[0]), "created_at": row[1]} for row in rows]


def recent_scans(limit: int = 10) -> list[dict[str, Any]]:
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM scans ORDER BY id DESC LIMIT ?", (limit,))]
