import argparse
from pathlib import Path

from unmet_demand.db import connect, init_db
from unmet_demand.ingest.adapters import ExportedDatasetAdapter
from unmet_demand.ingest.sources import insert_posts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import exported JSONL posts from Reddit, forums, issue trackers, or Q&A sites.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--source-type", choices=["reddit", "github", "forum", "community_qa"], required=True)
    parser.add_argument("--source")
    args = parser.parse_args()

    init_db()
    adapter = ExportedDatasetAdapter(args.path, source_type=args.source_type, source=args.source)
    with connect() as conn:
        count = insert_posts(conn, adapter.fetch())
    print(f"Imported {count} {args.source_type} records.")
