from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import requests

from unmet_demand.ingest.adapters import RateLimitedAdapter
from unmet_demand.ingest.sources import NormalizedPost, insert_posts, load_exported_jsonl, normalize_exported_record


def load_reddit_export(path: Path) -> list[NormalizedPost]:
    return load_exported_jsonl(path, source_type="reddit", source="reddit_export")


class RedditAPIAdapter(RateLimitedAdapter):
    """Minimal official Reddit API adapter.

    Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET. It is intentionally small
    and optional so the MVP still works from exported datasets with no API keys.
    """

    token_url = "https://www.reddit.com/api/v1/access_token"
    listing_url = "https://oauth.reddit.com/r/{subreddit}/search"

    def __init__(self, user_agent: str = "unmet-demand-intel/0.1", requests_per_minute: int = 30) -> None:
        super().__init__(requests_per_minute=requests_per_minute)
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = os.getenv("REDDIT_USER_AGENT", user_agent)

    def _token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to use live Reddit ingestion.")
        response = requests.post(
            self.token_url,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self.user_agent},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def search(self, subreddit: str, query: str, limit: int = 50) -> list[NormalizedPost]:
        token = self._token()
        self.wait()
        response = requests.get(
            self.listing_url.format(subreddit=subreddit),
            params={"q": query, "restrict_sr": 1, "sort": "new", "limit": min(limit, 100)},
            headers={"Authorization": f"Bearer {token}", "User-Agent": self.user_agent},
            timeout=20,
        )
        response.raise_for_status()
        posts: list[NormalizedPost] = []
        for child in response.json().get("data", {}).get("children", []):
            data = child.get("data", {})
            posts.append(
                normalize_exported_record(
                    {
                        "id": data.get("id"),
                        "author": data.get("author"),
                        "created_utc": str(data.get("created_utc") or ""),
                        "title": data.get("title"),
                        "body": data.get("selftext") or data.get("title") or "",
                        "url": f"https://reddit.com{data.get('permalink', '')}",
                    },
                    source_type="reddit",
                    source=f"reddit:r/{subreddit}",
                )
            )
        return posts


def ingest_reddit_export(conn: sqlite3.Connection, path: Path) -> int:
    return insert_posts(conn, load_reddit_export(path))
