from __future__ import annotations

import os

import requests

from unmet_demand.ingest.adapters import RateLimitedAdapter
from unmet_demand.ingest.sources import NormalizedPost, credibility_for


class GitHubIssuesAdapter(RateLimitedAdapter):
    """Live GitHub Issues search adapter using GitHub's REST search API."""

    search_url = "https://api.github.com/search/issues"

    def __init__(
        self,
        token: str | None = None,
        requests_per_minute: int = 20,
        session: requests.Session | None = None,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        super().__init__(requests_per_minute=requests_per_minute, max_retries=max_retries, backoff_seconds=backoff_seconds)
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 50, pages: int = 1) -> list[NormalizedPost]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        posts: list[NormalizedPost] = []
        for page in range(1, max(1, pages) + 1):
            response = self.request_with_backoff(
                lambda page=page: self.session.get(
                    self.search_url,
                    params={"q": query, "per_page": min(limit - len(posts), 100), "page": page, "sort": "updated", "order": "desc"},
                    headers=headers,
                    timeout=20,
                )
            )
            posts.extend(self._normalize_items(response.json().get("items", [])))
            if len(posts) >= limit:
                break
        return posts[:limit]

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
