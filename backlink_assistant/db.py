"""Stockage local des sites et des soumissions (SQLite, bibliotheque standard)."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB = "backlinks.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS site (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    url           TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    keywords      TEXT NOT NULL DEFAULT '',
    category      TEXT NOT NULL DEFAULT '',
    contact_email TEXT NOT NULL DEFAULT '',
    phone         TEXT NOT NULL DEFAULT '',
    address       TEXT NOT NULL DEFAULT '',
    city          TEXT NOT NULL DEFAULT '',
    country       TEXT NOT NULL DEFAULT 'FR',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submission (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id        INTEGER NOT NULL,
    directory_slug TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'todo',
    notes          TEXT NOT NULL DEFAULT '',
    submitted_at   TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    UNIQUE(site_id, directory_slug),
    FOREIGN KEY(site_id) REFERENCES site(id) ON DELETE CASCADE
);
"""

VALID_STATUSES = ("todo", "submitted", "approved", "rejected")


def connect(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def add_site(conn: sqlite3.Connection, **fields: Any) -> int:
    if not fields.get("name") or not fields.get("url"):
        raise ValueError("Un site doit avoir au moins un nom et une URL.")
    cols = (
        "name", "url", "description", "keywords", "category",
        "contact_email", "phone", "address", "city", "country",
    )
    values = {c: str(fields.get(c, "")).strip() for c in cols}
    if not values["country"]:
        values["country"] = "FR"
    cur = conn.execute(
        f"INSERT INTO site ({', '.join(cols)}, created_at) "
        f"VALUES ({', '.join(':' + c for c in cols)}, :created_at)",
        {**values, "created_at": _now()},
    )
    conn.commit()
    return int(cur.lastrowid)


def list_sites(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM site ORDER BY name COLLATE NOCASE").fetchall()
    return [dict(r) for r in rows]


def get_site(conn: sqlite3.Connection, site_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM site WHERE id = ?", (site_id,)).fetchone()
    return dict(row) if row else None


def update_site(conn: sqlite3.Connection, site_id: int, **fields: Any) -> bool:
    editable = (
        "name", "url", "description", "keywords", "category",
        "contact_email", "phone", "address", "city", "country",
    )
    updates = {c: str(fields[c]).strip() for c in editable if c in fields}
    if not updates:
        return False
    assignments = ", ".join(f"{c} = :{c}" for c in updates)
    cur = conn.execute(
        f"UPDATE site SET {assignments} WHERE id = :id",
        {**updates, "id": site_id},
    )
    conn.commit()
    return cur.rowcount > 0


def delete_site(conn: sqlite3.Connection, site_id: int) -> bool:
    cur = conn.execute("DELETE FROM site WHERE id = ?", (site_id,))
    conn.commit()
    return cur.rowcount > 0


def set_submission(
    conn: sqlite3.Connection,
    site_id: int,
    directory_slug: str,
    status: str = "todo",
    notes: str | None = None,
) -> dict:
    if status not in VALID_STATUSES:
        raise ValueError(f"Statut invalide : {status!r}. Attendu {VALID_STATUSES}.")
    now = _now()
    submitted_at = date.today().isoformat() if status in ("submitted", "approved") else ""
    existing = conn.execute(
        "SELECT * FROM submission WHERE site_id = ? AND directory_slug = ?",
        (site_id, directory_slug),
    ).fetchone()
    if existing:
        keep_submitted = existing["submitted_at"] or submitted_at
        conn.execute(
            "UPDATE submission SET status = ?, submitted_at = ?, "
            "notes = COALESCE(?, notes), updated_at = ? WHERE id = ?",
            (status, keep_submitted, notes, now, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO submission (site_id, directory_slug, status, notes, "
            "submitted_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (site_id, directory_slug, status, notes or "", submitted_at, now, now),
        )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM submission WHERE site_id = ? AND directory_slug = ?",
        (site_id, directory_slug),
    ).fetchone()
    return dict(row)


def list_submissions(conn: sqlite3.Connection, site_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM submission WHERE site_id = ? ORDER BY updated_at DESC",
        (site_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def submissions_by_slug(conn: sqlite3.Connection, site_id: int) -> dict[str, dict]:
    return {s["directory_slug"]: s for s in list_submissions(conn, site_id)}
