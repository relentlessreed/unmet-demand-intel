from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from unmet_demand.config import DEFAULT_SAMPLE_PATH
from unmet_demand.db import connect, init_db
from unmet_demand.ingest.scheduler import load_refresh_jobs, load_refresh_jobs_from_db, run_forever, run_refresh_jobs, upsert_refresh_job


def bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def seed_jobs_from_config(config_path: Path) -> int:
    jobs = load_refresh_jobs(config_path)
    with connect() as conn:
        for job in jobs:
            upsert_refresh_job(conn, job)
    return len(jobs)


def run_scheduler_service(run_once: bool = False) -> int:
    init_db()
    config_path = Path(os.getenv("UNMET_DEMAND_REFRESH_CONFIG", "data/source_refresh_jobs.example.json"))
    if bool_env("UNMET_DEMAND_SEED_REFRESH_JOBS", default=False):
        seed_jobs_from_config(config_path)

    with connect() as conn:
        jobs = load_refresh_jobs_from_db(conn)
        if not jobs and config_path.exists():
            jobs = load_refresh_jobs(config_path)
        if run_once:
            return run_refresh_jobs(conn, jobs)
        run_forever(conn, jobs)
    return 0


def run_pipeline_service() -> int:
    from unmet_demand.cluster.clusterer import cluster_requests
    from unmet_demand.embed.embedder import embed_requests
    from unmet_demand.extract.extractor import extract_requests
    from unmet_demand.ingest.sample_loader import load_sample_posts
    from unmet_demand.score.scorer import score_clusters

    init_db()
    sample_path = Path(os.getenv("UNMET_DEMAND_SAMPLE_PATH", str(DEFAULT_SAMPLE_PATH)))
    with connect() as conn:
        load_sample_posts(conn, sample_path=sample_path)
        extract_requests(conn)
        embed_requests(conn)
        cluster_requests(conn)
        score_clusters(conn)
    return 0


def run_dashboard_service() -> int:
    port = os.getenv("PORT", os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "src/unmet_demand/dashboard/app.py",
        "--server.headless",
        "true",
        "--server.port",
        port,
    ]
    return subprocess.call(cmd)


def main() -> int:
    mode = os.getenv("UNMET_DEMAND_SERVICE_MODE", "dashboard").lower()
    if mode == "dashboard":
        return run_dashboard_service()
    if mode == "scheduler":
        run_scheduler_service(run_once=False)
        return 0
    if mode == "scheduler-once":
        run_scheduler_service(run_once=True)
        return 0
    if mode == "pipeline":
        return run_pipeline_service()
    raise SystemExit(f"Unknown UNMET_DEMAND_SERVICE_MODE: {mode}")
