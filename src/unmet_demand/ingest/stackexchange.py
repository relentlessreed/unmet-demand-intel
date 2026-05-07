from __future__ import annotations

import requests

from unmet_demand.ingest.adapters import RateLimitedAdapter
from unmet_demand.ingest.sources import NormalizedPost, credibility_for


class StackExchangeAdapter(RateLimitedAdapter):
    """Live Stack Exchange Q&A adapter using the public search endpoint."""

    search_url = "https://api.stackexchange.com/2.3/search/advanced"

    def __init__(self, site: str = "stackoverflow", requests_per_minute: int = 20, session: requests.Session | None = None) -> None:
        super().__init__(requests_per_minute=requests_per_minute)
        self.site = site
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 50) -> list[NormalizedPost]:
        self.wait()
        response = self.session.get(
            self.search_url,
            params={
                "site": self.site,
                "q": query,
                "pagesize": min(limit, 100),
                "order": "desc",
                "sort": "activity",
                "filter": "withbody",
            },
            timeout=20,
        )
        response.raise_for_status()
        return self._normalize_items(response.json().get("items", [])[:limit])

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
