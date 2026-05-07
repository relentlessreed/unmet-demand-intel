from unmet_demand.db import connect, init_db
from unmet_demand.score.scorer import score_clusters


if __name__ == "__main__":
    init_db()
    with connect() as conn:
        count = score_clusters(conn)
    print(f"Scored {count} clusters.")
