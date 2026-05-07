from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from unmet_demand.ingest.discourse import DiscourseForumAdapter
from unmet_demand.ingest.github import GitHubIssuesAdapter
from unmet_demand.ingest.sources import NormalizedPost, insert_posts
from unmet_demand.ingest.stackexchange import StackExchangeAdapter


@dataclass(frozen=True)
class RefreshJob:
    name: str
    source: str
    query: str
    limit: int = 50
    pages: int = 1
    interval_minutes: int = 60
    base_url: str | None = None
    site: str = "stackoverflow"
    requests_per_minute: int = 20
    max_retries: int = 3
    backoff_seconds: float = 1.0


def load_refresh_jobs(path: Path) -> list[RefreshJob]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("jobs", payload if isinstance(payload, list) else [])
    return [RefreshJob(**item) for item in items]


def fetch_job_posts(job: RefreshJob) -> list[NormalizedPost]:
    if job.source == "discourse":
        if not job.base_url:
            raise ValueError(f"Job {job.name} requires base_url")
        return DiscourseForumAdapter(
            job.base_url,
            requests_per_minute=job.requests_per_minute,
            max_retries=job.max_retries,
            backoff_seconds=job.backoff_seconds,
        ).search(job.query, limit=job.limit, pages=job.pages)
    if job.source == "github":
        return GitHubIssuesAdapter(
            requests_per_minute=job.requests_per_minute,
            max_retries=job.max_retries,
            backoff_seconds=job.backoff_seconds,
        ).search(job.query, limit=job.limit, pages=job.pages)
    if job.source == "stackexchange":
        return StackExchangeAdapter(
            site=job.site,
            requests_per_minute=job.requests_per_minute,
            max_retries=job.max_retries,
            backoff_seconds=job.backoff_seconds,
        ).search(job.query, limit=job.limit, pages=job.pages)
    raise ValueError(f"Unsupported source: {job.source}")


def record_refresh_run(conn: sqlite3.Connection, job: RefreshJob, status: str, records_imported: int = 0, error: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO source_refresh_runs
            (job_name, source_kind, query, status, records_imported, error, finished_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (job.name, job.source, job.query, status, records_imported, error),
    )
    conn.commit()


def run_refresh_job(conn: sqlite3.Connection, job: RefreshJob) -> int:
    try:
        posts = fetch_job_posts(job)
        count = insert_posts(conn, posts)
        record_refresh_run(conn, job, "success", records_imported=count)
        return count
    except Exception as exc:
        record_refresh_run(conn, job, "failed", error=str(exc))
        raise


def run_refresh_jobs(conn: sqlite3.Connection, jobs: list[RefreshJob]) -> int:
    return sum(run_refresh_job(conn, job) for job in jobs)


def run_forever(conn: sqlite3.Connection, jobs: list[RefreshJob]) -> None:
    next_run = {job.name: 0.0 for job in jobs}
    while True:
        now = time.monotonic()
        for job in jobs:
            if now >= next_run[job.name]:
                run_refresh_job(conn, job)
                next_run[job.name] = now + job.interval_minutes * 60
        time.sleep(5)
