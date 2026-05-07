from unmet_demand.db import connect, init_db
from unmet_demand.ingest.sample_loader import load_sample_posts


if __name__ == "__main__":
    init_db()
    with connect() as conn:
        loaded = load_sample_posts(conn)
    print(f"Loaded {loaded} sample posts.")
