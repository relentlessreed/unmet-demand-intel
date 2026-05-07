import argparse

from unmet_demand.db import connect, init_db
from unmet_demand.review import update_cluster_review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set human review status for a scored cluster.")
    parser.add_argument("cluster_id", type=int)
    parser.add_argument("status", choices=["unreviewed", "accepted", "watchlist", "rejected"])
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    init_db()
    with connect() as conn:
        update_cluster_review(conn, args.cluster_id, args.status, args.notes)
    print(f"Cluster {args.cluster_id} marked {args.status}.")
