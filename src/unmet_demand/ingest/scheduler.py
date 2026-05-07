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


SOURCE_POLICIES = {
    "discourse": {
        "pages": 2,
        "requests_per_minute": 20,
        "max_retries": 4,
        "backoff_seconds": 1.5,
    },
    "github": {
        "pages": 2,
        "requests_per_minute": 20,
        "max_retries": 3,
        "backoff_seconds": 2.0,
    },
    "stackexchange": {
        "pages": 1,
        "requests_per_minute": 15,
        "max_retries": 3,
        "backoff_seconds": 2.0,
    },
}


@dataclass(frozen=True)
class RefreshJob:
    name: str
    source: str
    query: str
    limit: int = 50
    pages: int = 0
    interval_minutes: int = 60
    base_url: str | None = None
    site: str = "stackoverflow"
    requests_per_minute: int = 0
    max_retries: int | None = None
    backoff_seconds: float | None = None


def with_source_policy(job: RefreshJob) -> RefreshJob:
    policy = SOURCE_POLICIES.get(job.source, {})
    return RefreshJob(
        name=job.name,
        source=job.source,
        query=job.query,
        limit=job.limit,
        pages=job.pages or int(policy.get("pages", 1)),
        interval_minutes=job.interval_minutes,
        base_url=job.base_url,
        site=job.site,
        requests_per_minute=job.requests_per_minute or int(policy.get("requests_per_minute", 20)),
        max_retries=job.max_retries if job.max_retries is not None else int(policy.get("max_retries", 3)),
        backoff_seconds=job.backoff_seconds if job.backoff_seconds is not None else float(policy.get("backoff_seconds", 1.0)),
    )


def load_refresh_jobs(path: Path) -> list[RefreshJob]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("jobs", payload if isinstance(payload, list) else [])
    return [with_source_policy(RefreshJob(**item)) for item in items]


def row_to_refresh_job(row: sqlite3.Row) -> RefreshJob:
    job = RefreshJob(
        name=row["name"],
        source=row["source"],
        query=row["query"],
        limit=row["limit_count"],
        pages=row["pages"],
        interval_minutes=row["interval_minutes"],
        base_url=row["base_url"],
        site=row["site"] or "stackoverflow",
        requests_per_minute=row["requests_per_minute"] or 0,
        max_retries=row["max_retries"],
        backoff_seconds=row["backoff_seconds"],
    )
    return with_source_policy(job)


def load_refresh_jobs_from_db(conn: sqlite3.Connection, enabled_only: bool = True) -> list[RefreshJob]:
    where = "WHERE enabled = 1" if enabled_only else ""
    rows = conn.execute(f"SELECT * FROM source_refresh_jobs {where} ORDER BY name").fetchall()
    return [row_to_refresh_job(row) for row in rows]


def upsert_refresh_job(conn: sqlite3.Connection, job: RefreshJob, enabled: bool = True) -> None:
    resolved = with_source_policy(job)
    conn.execute(
        """
        INSERT INTO source_refresh_jobs
            (name, source, query, enabled, limit_count, pages, interval_minutes,
             base_url, site, requests_per_minute, max_retries, backoff_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            source = excluded.source,
            query = excluded.query,
            enabled = excluded.enabled,
            limit_count = excluded.limit_count,
            pages = excluded.pages,
            interval_minutes = excluded.interval_minutes,
            base_url = excluded.base_url,
            site = excluded.site,
            requests_per_minute = excluded.requests_per_minute,
            max_retries = excluded.max_retries,
            backoff_seconds = excluded.backoff_seconds,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            resolved.name,
            resolved.source,
            resolved.query,
            int(enabled),
            resolved.limit,
            resolved.pages,
            resolved.interval_minutes,
            resolved.base_url,
            resolved.site,
            resolved.requests_per_minute,
            resolved.max_retries,
            resolved.backoff_seconds,
        ),
    )
    conn.commit()


def delete_refresh_job(conn: sqlite3.Connection, name: str) -> None:
    conn.execute("DELETE FROM source_refresh_jobs WHERE name = ?", (name,))
    conn.commit()


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


def run_refresh_jobs(conn: sqlite3.Connection, jobs: list[RefreshJob], continue_on_error: bool = True) -> int:
    total = 0
    for job in jobs:
        try:
            total += run_refresh_job(conn, job)
        except Exception:
            if not continue_on_error:
                raise
    return total


def run_forever(conn: sqlite3.Connection, jobs: list[RefreshJob]) -> None:
    next_run = {job.name: 0.0 for job in jobs}
    while True:
        now = time.monotonic()
        for job in jobs:
            if now >= next_run[job.name]:
                try:
                    run_refresh_job(conn, job)
                except Exception as exc:
                    print(f"Refresh job failed: {job.name}: {exc}")
                next_run[job.name] = now + job.interval_minutes * 60
        time.sleep(5)
