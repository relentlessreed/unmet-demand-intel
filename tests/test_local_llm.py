from unmet_demand.extract.local_llm import enrich_cluster_with_local_llm


def test_local_llm_disabled_by_default(monkeypatch):
    monkeypatch.delenv("UNMET_DEMAND_USE_LOCAL_LLM", raising=False)

    assert enrich_cluster_with_local_llm("summary", ["quote"]) is None
