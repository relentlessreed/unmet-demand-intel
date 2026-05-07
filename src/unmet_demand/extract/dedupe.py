from __future__ import annotations

import re
import sqlite3
import json

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from unmet_demand.config import get_near_duplicate_threshold


def normalize_dedupe_text(*parts: str | None) -> str:
    text = " ".join(part or "" for part in parts).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def mark_duplicate_requests(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT id, problem, desired_solution, evidence_quote
        FROM extracted_requests
        ORDER BY id
        """
    ).fetchall()
    seen: dict[str, int] = {}
    duplicates = 0
    for row in rows:
        key = normalize_dedupe_text(row["problem"], row["desired_solution"], row["evidence_quote"][:120])
        duplicate_of = seen.get(key)
        if duplicate_of is None:
            seen[key] = row["id"]
            conn.execute(
                "UPDATE extracted_requests SET dedupe_key = ?, duplicate_of_request_id = NULL, is_duplicate = 0 WHERE id = ?",
                (key, row["id"]),
            )
        else:
            duplicates += 1
            conn.execute(
                "UPDATE extracted_requests SET dedupe_key = ?, duplicate_of_request_id = ?, is_duplicate = 1 WHERE id = ?",
                (key, duplicate_of, row["id"]),
            )
    conn.commit()
    return duplicates


def mark_near_duplicate_requests(conn: sqlite3.Connection, threshold: float | None = None) -> int:
    threshold = threshold or get_near_duplicate_threshold()
    rows = conn.execute(
        """
        SELECT id, embedding_json
        FROM extracted_requests
        WHERE is_duplicate = 0 AND embedding_json IS NOT NULL
        ORDER BY id
        """
    ).fetchall()
    if len(rows) < 2:
        return 0

    vectors = np.asarray([json.loads(row["embedding_json"]) for row in rows], dtype=float)
    similarities = cosine_similarity(vectors)
    duplicate_ids: set[int] = set()
    duplicates = 0
    for index, row in enumerate(rows):
        if row["id"] in duplicate_ids:
            continue
        for candidate_index in range(index + 1, len(rows)):
            candidate_id = rows[candidate_index]["id"]
            if candidate_id in duplicate_ids:
                continue
            if similarities[index, candidate_index] >= threshold:
                duplicate_ids.add(candidate_id)
                duplicates += 1
                conn.execute(
                    "UPDATE extracted_requests SET duplicate_of_request_id = ?, is_duplicate = 1 WHERE id = ?",
                    (row["id"], candidate_id),
                )
    conn.commit()
    return duplicates
