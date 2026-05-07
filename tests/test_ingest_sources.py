import sqlite3
from pathlib import Path

from unmet_demand.db import init_db
from unmet_demand.ingest.sources import insert_posts, load_exported_jsonl


def test_loads_exported_jsonl(tmp_path: Path):
    path = tmp_path / "reddit.jsonl"
    path.write_text('{"id":"abc","title":"Need plugin","selftext":"I wish there was a Godot exporter","author":"u"}\n')

    posts = load_exported_jsonl(path, source_type="reddit")

    assert len(posts) == 1
    assert posts[0].source_type == "reddit"
    assert posts[0].source_credibility_score > 3


def test_insert_posts_sets_hash_and_source_type(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    posts = load_exported_jsonl(
        tmp_path / "missing.jsonl",
        source_type="reddit",
    ) if False else []
    path = tmp_path / "forum.jsonl"
    path.write_text('{"id":"1","body":"I hate that export presets drift","source":"forum"}\n')
    posts = load_exported_jsonl(path, source_type="forum")

    assert insert_posts(conn, posts) == 1
    row = conn.execute("SELECT source_type, content_hash FROM raw_posts").fetchone()
    assert row["source_type"] == "forum"
    assert row["content_hash"]
