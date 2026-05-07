import argparse
from pathlib import Path

from unmet_demand.db import connect, init_db
from unmet_demand.ingest.scheduler import load_refresh_jobs, run_forever, run_refresh_jobs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run configured source refresh jobs.")
    parser.add_argument("--config", type=Path, default=Path("data/source_refresh_jobs.example.json"))
    parser.add_argument("--once", action="store_true", help="Run each job once and exit.")
    args = parser.parse_args()

    init_db()
    jobs = load_refresh_jobs(args.config)
    with connect() as conn:
        if args.once:
            count = run_refresh_jobs(conn, jobs)
            print(f"Refresh complete. Imported {count} records across {len(jobs)} jobs.")
        else:
            print(f"Running {len(jobs)} refresh jobs. Press Ctrl-C to stop.")
            run_forever(conn, jobs)
