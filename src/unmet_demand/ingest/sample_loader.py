from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from unmet_demand.config import DEFAULT_SAMPLE_PATH
from unmet_demand.ingest.sources import insert_posts, normalize_exported_record


def load_sample_posts(conn: sqlite3.Connection, sample_path: Path = DEFAULT_SAMPLE_PATH) -> int:
    posts = []
    with sample_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            post = json.loads(line)
            posts.append(normalize_exported_record(post, source_type="sample", source=post.get("source", "sample")))
    return insert_posts(conn, posts)
