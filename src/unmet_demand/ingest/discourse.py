from __future__ import annotations

from urllib.parse import urljoin

import requests

from unmet_demand.ingest.adapters import RateLimitedAdapter
from unmet_demand.ingest.sources import NormalizedPost, credibility_for


class DiscourseForumAdapter(RateLimitedAdapter):
    """Live adapter for public Discourse forums using their JSON endpoints."""

    def __init__(
        self,
        base_url: str,
        requests_per_minute: int = 30,
        session: requests.Session | None = None,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        super().__init__(requests_per_minute=requests_per_minute, max_retries=max_retries, backoff_seconds=backoff_seconds)
        self.base_url = base_url.rstrip("/") + "/"
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 25, pages: int = 1) -> list[NormalizedPost]:
        posts: list[NormalizedPost] = []
        for page in range(1, max(1, pages) + 1):
            response = self.request_with_backoff(
                lambda page=page: self.session.get(
                    urljoin(self.base_url, "search.json"),
                    params={"q": query, "page": page},
                    timeout=20,
                )
            )
            posts.extend(self._normalize_search_results(response.json(), limit=limit - len(posts)))
            if len(posts) >= limit:
                break
        return posts[:limit]

    def _normalize_search_results(self, payload: dict, limit: int) -> list[NormalizedPost]:
        posts: list[NormalizedPost] = []
        topics = {topic.get("id"): topic for topic in payload.get("topics", [])}
        for item in payload.get("posts", [])[:limit]:
            topic = topics.get(item.get("topic_id"), {})
            cooked = item.get("blurb") or item.get("cooked") or ""
            posts.append(
                NormalizedPost(
                    source=f"discourse:{self.base_url}",
                    source_type="forum",
                    external_id=str(item.get("id") or item.get("topic_id")),
                    author=item.get("username"),
                    created_at=item.get("created_at"),
                    title=topic.get("title") or item.get("topic_title"),
                    body=cooked,
                    url=urljoin(self.base_url, f"t/{topic.get('slug', '')}/{item.get('topic_id', '')}/{item.get('post_number', '')}"),
                    source_credibility_score=credibility_for("forum"),
                )
            )
        return posts
