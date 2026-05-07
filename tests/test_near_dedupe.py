import json
import sqlite3

from unmet_demand.db import init_db
from unmet_demand.extract.dedupe import mark_near_duplicate_requests


def test_mark_near_duplicate_requests(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("INSERT INTO raw_posts (source, external_id, body) VALUES ('sample', '1', 'body')")
    vectors = [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]]
    for index, vector in enumerate(vectors):
        conn.execute(
            """
            INSERT INTO extracted_requests
                (raw_post_id, problem, desired_solution, niche, urgency_score, emotion_score,
                 monetization_score, evidence_quote, embedding_json)
            VALUES (1, ?, 'solution', 'Godot', 2, 2, 2, 'quote', ?)
            """,
            (f"problem {index}", json.dumps(vector)),
        )
    conn.commit()

    duplicates = mark_near_duplicate_requests(conn, threshold=0.98)

    assert duplicates == 1
    assert conn.execute("SELECT COUNT(*) FROM extracted_requests WHERE is_duplicate = 1").fetchone()[0] == 1
