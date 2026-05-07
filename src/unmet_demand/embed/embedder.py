from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from unmet_demand.config import allow_model_download, get_embedding_model_name


@dataclass
class EmbeddingResult:
    vectors: np.ndarray
    backend: str


def request_text(row: sqlite3.Row | dict) -> str:
    return " | ".join(
        [
            row["problem"],
            row["desired_solution"],
            row["niche"] or "",
            row["evidence_quote"],
        ]
    )


def embed_texts(texts: list[str], model_name: str | None = None) -> EmbeddingResult:
    if not texts:
        return EmbeddingResult(np.empty((0, 0)), "none")

    model_name = model_name or get_embedding_model_name()
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name, local_files_only=not allow_model_download())
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return EmbeddingResult(np.asarray(vectors, dtype=float), f"sentence-transformers:{model_name}")
    except Exception as exc:
        print(f"Embedding fallback active: {exc}")
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=512)
        vectors = vectorizer.fit_transform(texts).toarray()
        return EmbeddingResult(np.asarray(vectors, dtype=float), "tfidf")


def embed_requests(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT * FROM extracted_requests ORDER BY id").fetchall()
    texts = [request_text(row) for row in rows]
    result = embed_texts(texts)
    for row, vector in zip(rows, result.vectors):
        conn.execute(
            "UPDATE extracted_requests SET embedding_json = ? WHERE id = ?",
            (json.dumps(vector.tolist()), row["id"]),
        )
    conn.commit()
    return result.backend
