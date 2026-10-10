"""Minimalna baza SQLite do śledzenia meczów i wiadomości Discord."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

DB_PATH = Path("data") / "pindolz.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS matches (
                match_id      INTEGER PRIMARY KEY,
                match_date    TEXT,
                match_time    TEXT,
                division      TEXT,
                opponent      TEXT,
                status        TEXT,
                score_team1   INTEGER,
                score_team2   INTEGER,
                winner_team_id INTEGER,
                updated_at    TEXT,
                finished_at   TEXT,
                notified_upcoming INTEGER DEFAULT 0,
                notified_result   INTEGER DEFAULT 0,
                msg_upcoming_id   INTEGER,
                msg_upcoming_ch   INTEGER,
                msg_live_id       INTEGER,
                msg_live_ch       INTEGER,
                msg_result_id     INTEGER,
                msg_result_ch     INTEGER,
                live_score_key    TEXT
            );

            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )


def get_config(key: str, default: str | None = None) -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def get_config_int(key: str, default: int | None = None) -> int | None:
    val = get_config(key)
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def set_config(key: str, value: str | None) -> None:
    with _connect() as conn:
        if value is None:
            conn.execute("DELETE FROM config WHERE key = ?", (key,))
        else:
            conn.execute(
                "INSERT INTO config(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )


def upsert_match(match_id: int, **fields: Any) -> None:
    allowed = {
        "match_date", "match_time", "division", "opponent", "status",
        "score_team1", "score_team2", "winner_team_id", "updated_at",
        "finished_at", "notified_upcoming", "notified_result",
        "msg_upcoming_id", "msg_upcoming_ch", "msg_live_id", "msg_live_ch",
        "msg_result_id", "msg_result_ch", "live_score_key",
    }
    data = {k: v for k, v in fields.items() if k in allowed}
    if not data:
        return

    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    updates = ", ".join(f"{k}=excluded.{k}" for k in data)

    with _connect() as conn:
        conn.execute(
            f"INSERT INTO matches (match_id, {cols}) VALUES (?, {placeholders}) "
            f"ON CONFLICT(match_id) DO UPDATE SET {updates}",
            (match_id, *data.values()),
        )


def get_match(match_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,)).fetchone()
        return dict(row) if row else None


def get_live_matches() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM matches WHERE status = 'live'").fetchall()
        return [dict(r) for r in rows]


def get_upcoming_notified() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM matches WHERE notified_upcoming = 1 AND status != 'finished'"
        ).fetchall()
        return [dict(r) for r in rows]


def mark_finished(match_id: int, finished_at: str | None = None) -> None:
    upsert_match(
        match_id,
        status="finished",
        finished_at=finished_at or datetime.utcnow().isoformat(),
    )


def cleanup_old(days: int = 30) -> int:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM matches WHERE status IN ('finished', 'cancelled') "
            "AND finished_at IS NOT NULL AND finished_at < ?",
            (cutoff,),
        )
        return cur.rowcount
