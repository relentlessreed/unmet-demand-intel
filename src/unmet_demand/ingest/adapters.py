from __future__ import annotations

from pathlib import Path

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

    def __init__(self, requests_per_minute: int = 30) -> None:
        self.rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)

    def wait(self) -> None:
        self.rate_limiter.wait()
