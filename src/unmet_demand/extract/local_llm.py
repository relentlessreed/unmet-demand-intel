from __future__ import annotations

import json
import urllib.error
import urllib.request

from unmet_demand.config import get_local_llm_model, get_local_llm_url, use_local_llm


def enrich_cluster_with_local_llm(summary: str, quotes: list[str]) -> dict[str, str] | None:
    if not use_local_llm():
        return None

    prompt = (
        "Summarize this unmet software demand cluster as JSON with keys "
        "summary and suggested_product_angle. Keep both under 25 words.\n\n"
        f"Current summary: {summary}\n"
        f"Evidence quotes: {json.dumps(quotes[:5])}"
    )
    payload = json.dumps(
        {
            "model": get_local_llm_model(),
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
    ).encode("utf-8")
    try:
        request = urllib.request.Request(
            get_local_llm_url(),
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = json.loads(response.read().decode("utf-8"))
        content = raw.get("response", "{}")
        parsed = json.loads(content)
        if parsed.get("summary") and parsed.get("suggested_product_angle"):
            return {
                "summary": str(parsed["summary"]),
                "suggested_product_angle": str(parsed["suggested_product_angle"]),
            }
    except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError) as exc:
        print(f"Local LLM enrichment fallback active: {exc}")
    return None
