from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SOURCE_CREDIBILITY = {
    "reddit": 3.4,
    "github": 4.2,
    "forum": 3.3,
    "community_qa": 3.1,
    "stackexchange": 3.6,
    "sample": 3.0,
}


@dataclass(frozen=True)
class NormalizedPost:
    source: str
    external_id: str
    body: str
    source_type: str = "sample"
    author: str | None = None
    created_at: str | None = None
    title: str | None = None
    url: str | None = None
    niche: str | None = None
    source_credibility_score: float = 3.0

    @property
    def content_hash(self) -> str:
        content = f"{self.title or ''}\n{self.body}".strip().lower()
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class RateLimiter:
    def __init__(self, requests_per_minute: int = 30) -> None:
        self.delay_seconds = 60 / max(1, requests_per_minute)
        self._last_call = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self._last_call = time.monotonic()


def credibility_for(source_type: str) -> float:
    return SOURCE_CREDIBILITY.get(source_type, 3.0)


def normalize_exported_record(record: dict, source_type: str, source: str | None = None) -> NormalizedPost:
    body = record.get("body") or record.get("text") or record.get("selftext") or record.get("comment") or ""
    title = record.get("title") or record.get("subject")
    external_id = str(record.get("external_id") or record.get("id") or record.get("url") or hashlib.sha1(body.encode()).hexdigest())
    resolved_source = source or record.get("source") or source_type
    return NormalizedPost(
        source=resolved_source,
        source_type=source_type,
        external_id=external_id,
        author=record.get("author") or record.get("user"),
        created_at=record.get("created_at") or record.get("created_utc") or record.get("timestamp"),
        title=title,
        body=body,
        url=record.get("url") or record.get("permalink") or record.get("html_url"),
        niche=record.get("niche"),
        source_credibility_score=float(record.get("source_credibility_score") or credibility_for(source_type)),
    )


def load_exported_jsonl(path: Path, source_type: str, source: str | None = None) -> list[NormalizedPost]:
    posts: list[NormalizedPost] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            posts.append(normalize_exported_record(json.loads(line), source_type=source_type, source=source))
    return posts


def insert_posts(conn: sqlite3.Connection, posts: Iterable[NormalizedPost]) -> int:
    count = 0
    for post in posts:
        if not post.body.strip():
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO raw_posts
                (source, source_type, external_id, author, created_at, title, body, url,
                 niche, content_hash, source_credibility_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.source,
                post.source_type,
                post.external_id,
                post.author,
                post.created_at,
                post.title,
                post.body,
                post.url,
                post.niche,
                post.content_hash,
                post.source_credibility_score,
            ),
        )
        count += 1
    conn.commit()
    return count
