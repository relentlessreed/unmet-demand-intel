from __future__ import annotations

import json
import sqlite3
from collections import Counter

from unmet_demand.extract.local_llm import enrich_cluster_with_local_llm


def bounded(value: float, low: float = 1.0, high: float = 5.0) -> float:
    return max(low, min(high, value))


def infer_feasibility(summary_text: str) -> float:
    lowered = summary_text.lower()
    score = 3.5
    if "plugin" in lowered or "tool" in lowered or "asset" in lowered:
        score += 0.7
    if "ai" in lowered or "multiplayer" in lowered or "marketplace" in lowered:
        score -= 0.4
    return bounded(score)


def infer_novelty(_summary_text: str) -> float:
    # TODO: Compare against app stores, GitHub, asset marketplaces, and search results.
    return 3.0


def score_opportunity(
    frequency_score: float,
    pain_score: float,
    urgency_score: float,
    monetization_score: float,
    feasibility_score: float,
    novelty_score: float,
) -> float:
    return round(
        0.30 * frequency_score
        + 0.20 * pain_score
        + 0.15 * urgency_score
        + 0.15 * monetization_score
        + 0.10 * feasibility_score
        + 0.10 * novelty_score,
        3,
    )


def summarize_cluster(rows: list[sqlite3.Row]) -> str:
    niches = Counter(row["niche"] or "Software tools" for row in rows)
    desired = Counter(row["desired_solution"] for row in rows)
    return f"{niches.most_common(1)[0][0]} demand: {desired.most_common(1)[0][0]}"


def suggest_product_angle(rows: list[sqlite3.Row]) -> str:
    text = " ".join(row["desired_solution"] for row in rows).lower()
    if "plugin" in text or "godot" in text:
        return "Package a focused Godot plugin with templates, docs, and paid support."
    if "asset" in text or "sprite" in text or "tileset" in text:
        return "Create a production-ready asset/tool bundle for indie teams."
    return "Build a narrow workflow tool that removes the repeated manual step."


def source_credibility_for_rows(rows: list[sqlite3.Row]) -> float:
    return sum(row["source_credibility_score"] or 3.0 for row in rows) / len(rows)


def score_clusters(conn: sqlite3.Connection) -> int:
    conn.execute("DELETE FROM request_clusters")
    rows = conn.execute(
        """
        SELECT er.*, rp.source_credibility_score
        FROM extracted_requests er
        JOIN raw_posts rp ON rp.id = er.raw_post_id
        WHERE er.cluster_id IS NOT NULL AND er.is_duplicate = 0
        ORDER BY er.cluster_id, er.id
        """
    ).fetchall()
    if not rows:
        conn.commit()
        return 0

    counts = Counter(row["cluster_id"] for row in rows)
    max_count = max(counts.values())
    written = 0
    for cluster_id in sorted(counts):
        cluster_rows = [row for row in rows if row["cluster_id"] == cluster_id]
        request_count = len(cluster_rows)
        avg_urgency = sum(row["urgency_score"] for row in cluster_rows) / request_count
        avg_emotion = sum(row["emotion_score"] for row in cluster_rows) / request_count
        avg_monetization = sum(row["monetization_score"] for row in cluster_rows) / request_count
        frequency_score = 1 + 4 * (request_count / max_count)
        summary = summarize_cluster(cluster_rows)
        feasibility = infer_feasibility(summary)
        novelty = infer_novelty(summary)
        quotes = [row["evidence_quote"] for row in cluster_rows[:5]]
        llm_enrichment = enrich_cluster_with_local_llm(summary, quotes)
        product_angle = suggest_product_angle(cluster_rows)
        if llm_enrichment:
            summary = llm_enrichment["summary"]
            product_angle = llm_enrichment["suggested_product_angle"]
        source_credibility = source_credibility_for_rows(cluster_rows)
        credibility_adjustment = (source_credibility - 3.0) * 0.08
        opportunity = score_opportunity(frequency_score, avg_emotion, avg_urgency, avg_monetization, feasibility, novelty)
        opportunity = round(bounded(opportunity + credibility_adjustment), 3)
        conn.execute(
            """
            INSERT INTO request_clusters
                (cluster_label, summary, suggested_product_angle, request_count, avg_urgency,
                 avg_emotion, avg_monetization, feasibility_score, novelty_score,
                 source_credibility_score, opportunity_score, representative_quotes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cluster_id,
                summary,
                product_angle,
                request_count,
                avg_urgency,
                avg_emotion,
                avg_monetization,
                feasibility,
                novelty,
                source_credibility,
                opportunity,
                json.dumps(quotes),
            ),
        )
        written += 1
    conn.commit()
    return written
