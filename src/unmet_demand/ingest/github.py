from __future__ import annotations

import os

import requests

from unmet_demand.ingest.adapters import RateLimitedAdapter
from unmet_demand.ingest.sources import NormalizedPost, credibility_for


class GitHubIssuesAdapter(RateLimitedAdapter):
    """Live GitHub Issues search adapter using GitHub's REST search API."""

    search_url = "https://api.github.com/search/issues"

    def __init__(self, token: str | None = None, requests_per_minute: int = 20, session: requests.Session | None = None) -> None:
        super().__init__(requests_per_minute=requests_per_minute)
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 50) -> list[NormalizedPost]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.wait()
        response = self.session.get(
            self.search_url,
            params={"q": query, "per_page": min(limit, 100), "sort": "updated", "order": "desc"},
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        return self._normalize_items(response.json().get("items", [])[:limit])

    def _normalize_items(self, items: list[dict]) -> list[NormalizedPost]:
        posts: list[NormalizedPost] = []
        for item in items:
            user = item.get("user") or {}
            posts.append(
                NormalizedPost(
                    source="github_issues",
                    source_type="github",
                    external_id=str(item.get("id") or item.get("html_url")),
                    author=user.get("login"),
                    created_at=item.get("created_at"),
                    title=item.get("title"),
                    body=item.get("body") or item.get("title") or "",
                    url=item.get("html_url"),
                    source_credibility_score=credibility_for("github"),
                )
            )
        return posts
