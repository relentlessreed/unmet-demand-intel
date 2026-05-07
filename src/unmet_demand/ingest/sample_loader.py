from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from unmet_demand.config import DEFAULT_SAMPLE_PATH


def load_sample_posts(conn: sqlite3.Connection, sample_path: Path = DEFAULT_SAMPLE_PATH) -> int:
    count = 0
    with sample_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            post = json.loads(line)
            conn.execute(
                """
                INSERT OR REPLACE INTO raw_posts
                    (source, external_id, author, created_at, title, body, url, niche)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post["source"],
                    post["external_id"],
                    post.get("author"),
                    post.get("created_at"),
                    post.get("title"),
                    post["body"],
                    post.get("url"),
                    post.get("niche"),
                ),
            )
            count += 1
    conn.commit()
    return count
