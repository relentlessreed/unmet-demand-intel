from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from unmet_demand.config import get_db_path


SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_type TEXT DEFAULT 'sample',
    external_id TEXT NOT NULL,
    author TEXT,
    created_at TEXT,
    title TEXT,
    body TEXT NOT NULL,
    url TEXT,
    niche TEXT,
    content_hash TEXT,
    source_credibility_score REAL NOT NULL DEFAULT 3.0,
    UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS extracted_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_post_id INTEGER NOT NULL,
    problem TEXT NOT NULL,
    desired_solution TEXT NOT NULL,
    niche TEXT,
    urgency_score INTEGER NOT NULL CHECK (urgency_score BETWEEN 1 AND 5),
    emotion_score INTEGER NOT NULL CHECK (emotion_score BETWEEN 1 AND 5),
    monetization_score INTEGER NOT NULL CHECK (monetization_score BETWEEN 1 AND 5),
    evidence_quote TEXT NOT NULL,
    dedupe_key TEXT,
    duplicate_of_request_id INTEGER,
    is_duplicate INTEGER NOT NULL DEFAULT 0,
    embedding_json TEXT,
    cluster_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(raw_post_id) REFERENCES raw_posts(id)
);

CREATE TABLE IF NOT EXISTS request_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_label INTEGER NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    suggested_product_angle TEXT NOT NULL,
    request_count INTEGER NOT NULL,
    avg_urgency REAL NOT NULL,
    avg_emotion REAL NOT NULL,
    avg_monetization REAL NOT NULL,
    feasibility_score REAL NOT NULL,
    novelty_score REAL NOT NULL,
    source_credibility_score REAL NOT NULL DEFAULT 3.0,
    opportunity_score REAL NOT NULL,
    representative_quotes TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'unreviewed',
    review_notes TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


MIGRATIONS = {
    "raw_posts": {
        "source_type": "TEXT DEFAULT 'sample'",
        "content_hash": "TEXT",
        "source_credibility_score": "REAL NOT NULL DEFAULT 3.0",
    },
    "extracted_requests": {
        "dedupe_key": "TEXT",
        "duplicate_of_request_id": "INTEGER",
        "is_duplicate": "INTEGER NOT NULL DEFAULT 0",
    },
    "request_clusters": {
        "source_credibility_score": "REAL NOT NULL DEFAULT 3.0",
        "review_status": "TEXT NOT NULL DEFAULT 'unreviewed'",
        "review_notes": "TEXT",
    },
}


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        apply_migrations(conn)


def apply_migrations(conn: sqlite3.Connection) -> None:
    for table, columns in MIGRATIONS.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for column, column_type in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
    conn.commit()


def reset_pipeline_tables(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM request_clusters")
    conn.execute("DELETE FROM extracted_requests")
    conn.commit()


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]
