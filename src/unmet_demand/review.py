from __future__ import annotations

import sqlite3


VALID_REVIEW_STATUSES = {"unreviewed", "accepted", "rejected", "watchlist"}


def update_cluster_review(conn: sqlite3.Connection, cluster_id: int, status: str, notes: str | None = None) -> None:
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {status}")
    current = conn.execute(
        "SELECT id, cluster_label, review_status, summary FROM request_clusters WHERE id = ?",
        (cluster_id,),
    ).fetchone()
    if current is None:
        raise ValueError(f"Cluster not found: {cluster_id}")
    conn.execute(
        """
        UPDATE request_clusters
        SET review_status = ?, review_notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, notes, cluster_id),
    )
    conn.execute(
        """
        INSERT INTO review_events
            (cluster_id, cluster_label, previous_status, new_status, notes, summary_snapshot)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            current["id"],
            current["cluster_label"],
            current["review_status"],
            status,
            notes,
            current["summary"],
        ),
    )
    conn.commit()


def get_review_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {status: 0 for status in VALID_REVIEW_STATUSES}
    rows = conn.execute("SELECT review_status, COUNT(*) AS count FROM request_clusters GROUP BY review_status").fetchall()
    for row in rows:
        counts[row["review_status"]] = row["count"]
    return counts


def latest_review_for_label(conn: sqlite3.Connection, cluster_label: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM review_events
        WHERE cluster_label = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (cluster_label,),
    ).fetchone()
