import sqlite3

from unmet_demand.db import init_db
from unmet_demand.ingest.scheduler import (
    RefreshJob,
    delete_refresh_job,
    load_refresh_jobs_from_db,
    record_refresh_run,
    run_refresh_jobs,
    upsert_refresh_job,
    with_source_policy,
)


def test_record_refresh_run(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    job = RefreshJob(name="github-test", source="github", query="godot plugin")

    record_refresh_run(conn, job, "success", records_imported=3)

    row = conn.execute("SELECT job_name, status, records_imported FROM source_refresh_runs").fetchone()
    assert row["job_name"] == "github-test"
    assert row["status"] == "success"
    assert row["records_imported"] == 3


def test_upsert_load_and_delete_refresh_job(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    upsert_refresh_job(conn, RefreshJob(name="job", source="github", query="godot plugin", pages=0), enabled=True)
    jobs = load_refresh_jobs_from_db(conn)

    assert len(jobs) == 1
    assert jobs[0].name == "job"
    assert jobs[0].pages == 2
    assert jobs[0].backoff_seconds == 2.0

    delete_refresh_job(conn, "job")

    assert load_refresh_jobs_from_db(conn) == []


def test_source_policy_keeps_explicit_overrides():
    job = with_source_policy(
        RefreshJob(
            name="forum",
            source="discourse",
            query="godot",
            pages=5,
            requests_per_minute=7,
            max_retries=1,
            backoff_seconds=0.5,
        )
    )

    assert job.pages == 5
    assert job.requests_per_minute == 7
    assert job.max_retries == 1
    assert job.backoff_seconds == 0.5


def test_run_refresh_jobs_continues_after_failure(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    def fail_fetch(_job):
        raise RuntimeError("network down")

    monkeypatch.setattr("unmet_demand.ingest.scheduler.fetch_job_posts", fail_fetch)
    total = run_refresh_jobs(conn, [RefreshJob(name="bad", source="github", query="godot")])

    assert total == 0
    row = conn.execute("SELECT status, error FROM source_refresh_runs").fetchone()
    assert row["status"] == "failed"
    assert "network down" in row["error"]
