import argparse
from pathlib import Path

from unmet_demand.db import connect, init_db
from unmet_demand.ingest.scheduler import load_refresh_jobs, load_refresh_jobs_from_db, run_forever, run_refresh_jobs, upsert_refresh_job


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run configured source refresh jobs.")
    parser.add_argument("--config", type=Path, default=Path("data/source_refresh_jobs.example.json"))
    parser.add_argument("--once", action="store_true", help="Run each job once and exit.")
    parser.add_argument("--from-db", action="store_true", help="Load editable jobs from SQLite instead of JSON.")
    parser.add_argument("--seed-db", action="store_true", help="Insert or update SQLite jobs from --config, then exit.")
    args = parser.parse_args()

    init_db()
    with connect() as conn:
        if args.seed_db:
            jobs = load_refresh_jobs(args.config)
            for job in jobs:
                upsert_refresh_job(conn, job)
            print(f"Seeded {len(jobs)} refresh jobs into SQLite.")
            raise SystemExit(0)

        jobs = load_refresh_jobs_from_db(conn) if args.from_db else load_refresh_jobs(args.config)
        if args.once:
            count = run_refresh_jobs(conn, jobs)
            print(f"Refresh complete. Imported {count} records across {len(jobs)} jobs.")
        else:
            print(f"Running {len(jobs)} refresh jobs. Press Ctrl-C to stop.")
            run_forever(conn, jobs)
