from __future__ import annotations

import sqlite3


VALID_REVIEW_STATUSES = {"unreviewed", "accepted", "rejected", "watchlist"}


def update_cluster_review(conn: sqlite3.Connection, cluster_id: int, status: str, notes: str | None = None) -> None:
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {status}")
    conn.execute(
        """
        UPDATE request_clusters
        SET review_status = ?, review_notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, notes, cluster_id),
    )
    conn.commit()


def get_review_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {status: 0 for status in VALID_REVIEW_STATUSES}
    rows = conn.execute("SELECT review_status, COUNT(*) AS count FROM request_clusters GROUP BY review_status").fetchall()
    for row in rows:
        counts[row["review_status"]] = row["count"]
    return counts
