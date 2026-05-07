from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import requests

from unmet_demand.ingest.sources import NormalizedPost, RateLimiter, load_exported_jsonl


class ExportedDatasetAdapter:
    """Loads exported JSONL from forums, issue trackers, or Q&A sites."""

    def __init__(self, path: Path, source_type: str, source: str | None = None) -> None:
        self.path = path
        self.source_type = source_type
        self.source = source

    def fetch(self) -> list[NormalizedPost]:
        return load_exported_jsonl(self.path, source_type=self.source_type, source=self.source)


class RateLimitedAdapter:
    """Small base wrapper for future API-backed adapters."""

    def __init__(self, requests_per_minute: int = 30, max_retries: int = 3, backoff_seconds: float = 1.0) -> None:
        self.rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def wait(self) -> None:
        self.rate_limiter.wait()

    def request_with_backoff(self, request_fn: Callable[[], requests.Response]) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self.wait()
            try:
                response = request_fn()
                if response.status_code not in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    return response
                last_error = requests.HTTPError(f"Retryable HTTP {response.status_code}", response=response)
            except requests.RequestException as exc:
                last_error = exc
            if attempt < self.max_retries:
                time.sleep(self.backoff_seconds * (2**attempt))
        if last_error:
            raise last_error
        raise RuntimeError("Request failed without an exception")
