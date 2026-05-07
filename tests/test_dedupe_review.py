import sqlite3

from unmet_demand.db import init_db
from unmet_demand.extract.dedupe import mark_duplicate_requests
from unmet_demand.review import get_review_counts, latest_review_for_label, update_cluster_review


def test_mark_duplicate_requests(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("INSERT INTO raw_posts (source, external_id, body) VALUES ('sample', '1', 'body')")
    for _ in range(2):
        conn.execute(
            """
            INSERT INTO extracted_requests
                (raw_post_id, problem, desired_solution, niche, urgency_score, emotion_score, monetization_score, evidence_quote)
            VALUES (1, 'same problem', 'same solution', 'Godot', 2, 2, 2, 'same quote')
            """
        )
    conn.commit()

    duplicates = mark_duplicate_requests(conn)

    assert duplicates == 1
    assert conn.execute("SELECT COUNT(*) FROM extracted_requests WHERE is_duplicate = 1").fetchone()[0] == 1


def test_update_cluster_review(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        INSERT INTO request_clusters
            (cluster_label, summary, suggested_product_angle, request_count, avg_urgency,
             avg_emotion, avg_monetization, feasibility_score, novelty_score,
             opportunity_score, representative_quotes)
        VALUES (1, 'summary', 'angle', 2, 3, 3, 3, 3, 3, 3, '[]')
        """
    )
    conn.commit()

    update_cluster_review(conn, 1, "accepted", "promising")

    row = conn.execute("SELECT review_status, review_notes FROM request_clusters WHERE id = 1").fetchone()
    assert row["review_status"] == "accepted"
    assert row["review_notes"] == "promising"
    assert get_review_counts(conn)["accepted"] == 1
    event = latest_review_for_label(conn, 1)
    assert event["previous_status"] == "unreviewed"
    assert event["new_status"] == "accepted"
