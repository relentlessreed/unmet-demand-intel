from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from unmet_demand.db import reset_pipeline_tables
from unmet_demand.extract.patterns import (
    EMOTION_TERMS,
    MONETIZATION_TERMS,
    REQUEST_PATTERNS,
    URGENCY_TERMS,
)


@dataclass(frozen=True)
class ExtractedRequest:
    raw_post_id: int
    problem: str
    desired_solution: str
    niche: str
    urgency_score: int
    emotion_score: int
    monetization_score: int
    evidence_quote: str


def _score_terms(text: str, term_scores: dict[str, int], default: int = 2) -> int:
    lowered = text.lower()
    score = default
    for term, value in term_scores.items():
        if term in lowered:
            score = max(score, value)
    return min(5, max(1, score))


def infer_niche(text: str, fallback: str | None = None) -> str:
    lowered = text.lower()
    if "godot" in lowered:
        return "Godot"
    if "plugin" in lowered or "addon" in lowered:
        return "Game dev plugins"
    if "asset" in lowered or "sprite" in lowered or "tileset" in lowered:
        return "Game assets"
    if "indie" in lowered or "steam" in lowered:
        return "Indie dev tools"
    return fallback or "Software tools"


def clean_fragment(fragment: str) -> str:
    fragment = re.sub(r"\s+", " ", fragment).strip(" -,:;")
    return fragment[:240]


def summarize_problem(text: str, fragment: str) -> str:
    fragment = clean_fragment(fragment)
    if fragment:
        return f"Developer cannot easily find or use {fragment}."
    sentence = re.split(r"[.?!]", text.strip())[0]
    return clean_fragment(sentence) or "Developer has an unresolved workflow problem."


def summarize_solution(fragment: str) -> str:
    fragment = clean_fragment(fragment)
    if not fragment:
        return "A focused tool or plugin that removes the repeated manual workflow."
    if fragment.lower().startswith(("a ", "an ", "the ")):
        return fragment[0].upper() + fragment[1:]
    return f"A tool/plugin for {fragment}."


def extract_from_text(raw_post_id: int, title: str | None, body: str, niche: str | None = None) -> list[ExtractedRequest]:
    text = f"{title or ''}\n{body}".strip()
    results: list[ExtractedRequest] = []
    seen_matches: set[tuple[int, str]] = set()
    for pattern in REQUEST_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            quote_start = max(0, start - 80)
            quote_end = min(len(text), end + 120)
            evidence = clean_fragment(text[quote_start:quote_end])
            fragment = clean_fragment(match.groupdict().get("request", ""))
            seen_key = (start, fragment.lower())
            if seen_key in seen_matches:
                continue
            seen_matches.add(seen_key)
            context = f"{evidence} {fragment}"
            results.append(
                ExtractedRequest(
                    raw_post_id=raw_post_id,
                    problem=summarize_problem(text, fragment),
                    desired_solution=summarize_solution(fragment),
                    niche=infer_niche(context, niche),
                    urgency_score=_score_terms(context, URGENCY_TERMS, default=2),
                    emotion_score=_score_terms(context, EMOTION_TERMS, default=2),
                    monetization_score=_score_terms(context, MONETIZATION_TERMS, default=2),
                    evidence_quote=evidence,
                )
            )
    return results


def extract_requests(conn: sqlite3.Connection, clear_existing: bool = True) -> int:
    if clear_existing:
        reset_pipeline_tables(conn)
    posts = conn.execute("SELECT id, title, body, niche FROM raw_posts ORDER BY id").fetchall()
    total = 0
    for post in posts:
        for item in extract_from_text(post["id"], post["title"], post["body"], post["niche"]):
            conn.execute(
                """
                INSERT INTO extracted_requests
                    (raw_post_id, problem, desired_solution, niche, urgency_score,
                     emotion_score, monetization_score, evidence_quote)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.raw_post_id,
                    item.problem,
                    item.desired_solution,
                    item.niche,
                    item.urgency_score,
                    item.emotion_score,
                    item.monetization_score,
                    item.evidence_quote,
                ),
            )
            total += 1
    conn.commit()
    return total
