from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from unmet_demand.config import get_db_path


SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    author TEXT,
    created_at TEXT,
    title TEXT,
    body TEXT NOT NULL,
    url TEXT,
    niche TEXT,
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
    opportunity_score REAL NOT NULL,
    representative_quotes TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def reset_pipeline_tables(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM request_clusters")
    conn.execute("DELETE FROM extracted_requests")
    conn.commit()


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]
