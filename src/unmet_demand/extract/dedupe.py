from __future__ import annotations

import re
import sqlite3


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
