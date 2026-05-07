from __future__ import annotations

import json
import sqlite3

import numpy as np

from unmet_demand.embed.embedder import embed_requests


def _load_vectors(rows: list[sqlite3.Row]) -> np.ndarray:
    vectors = [json.loads(row["embedding_json"]) for row in rows if row["embedding_json"]]
    if not vectors:
        return np.empty((0, 0))
    return np.asarray(vectors, dtype=float)


def _normalize_labels(labels: list[int]) -> list[int]:
    mapping: dict[int, int] = {}
    next_label = 0
    normalized: list[int] = []
    for label in labels:
        if label == -1:
            label = next_label
            next_label += 1
        elif label not in mapping:
            mapping[label] = next_label
            next_label += 1
        normalized.append(mapping.get(label, label))
    return normalized


def cluster_vectors(vectors: np.ndarray) -> tuple[list[int], str]:
    n = len(vectors)
    if n == 0:
        return [], "none"
    if n == 1:
        return [0], "single"

    try:
        import hdbscan

        min_cluster_size = 3 if n >= 6 else 2
        labels = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean").fit_predict(vectors)
        return _normalize_labels([int(label) for label in labels]), "hdbscan"
    except Exception as exc:
        print(f"HDBSCAN fallback active: {exc}")

    try:
        from sklearn.cluster import AgglomerativeClustering

        distance_threshold = 0.9
        model = AgglomerativeClustering(n_clusters=None, distance_threshold=distance_threshold, metric="cosine", linkage="average")
        labels = model.fit_predict(vectors)
        return _normalize_labels([int(label) for label in labels]), "agglomerative"
    except Exception as exc:
        print(f"Agglomerative fallback active: {exc}")

    from sklearn.cluster import DBSCAN

    labels = DBSCAN(eps=0.65, min_samples=2, metric="cosine").fit_predict(vectors)
    return _normalize_labels([int(label) for label in labels]), "dbscan"


def cluster_requests(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT * FROM extracted_requests ORDER BY id").fetchall()
    if any(row["embedding_json"] is None for row in rows):
        embed_requests(conn)
        rows = conn.execute("SELECT * FROM extracted_requests ORDER BY id").fetchall()
    vectors = _load_vectors(rows)
    labels, backend = cluster_vectors(vectors)
    for row, label in zip(rows, labels):
        conn.execute("UPDATE extracted_requests SET cluster_id = ? WHERE id = ?", (label, row["id"]))
    conn.commit()
    return backend
