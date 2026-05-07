from __future__ import annotations

import requests

from unmet_demand.ingest.adapters import RateLimitedAdapter
from unmet_demand.ingest.sources import NormalizedPost, credibility_for


class StackExchangeAdapter(RateLimitedAdapter):
    """Live Stack Exchange Q&A adapter using the public search endpoint."""

    search_url = "https://api.stackexchange.com/2.3/search/advanced"

    def __init__(
        self,
        site: str = "stackoverflow",
        requests_per_minute: int = 20,
        session: requests.Session | None = None,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        super().__init__(requests_per_minute=requests_per_minute, max_retries=max_retries, backoff_seconds=backoff_seconds)
        self.site = site
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 50, pages: int = 1) -> list[NormalizedPost]:
        posts: list[NormalizedPost] = []
        for page in range(1, max(1, pages) + 1):
            response = self.request_with_backoff(
                lambda page=page: self.session.get(
                    self.search_url,
                    params={
                        "site": self.site,
                        "q": query,
                        "pagesize": min(limit - len(posts), 100),
                        "page": page,
                        "order": "desc",
                        "sort": "activity",
                        "filter": "withbody",
                    },
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
            owner = item.get("owner") or {}
            posts.append(
                NormalizedPost(
                    source=f"stackexchange:{self.site}",
                    source_type="stackexchange",
                    external_id=str(item.get("question_id") or item.get("link")),
                    author=owner.get("display_name"),
                    created_at=str(item.get("creation_date") or ""),
                    title=item.get("title"),
                    body=item.get("body") or item.get("title") or "",
                    url=item.get("link"),
                    source_credibility_score=credibility_for("stackexchange"),
                )
            )
        return posts
