# Unmet Demand Intelligence System

Local-first MVP for detecting repeated unmet software and product requests from public text. The current version runs end-to-end on offline sample data: load posts, extract request/frustration candidates, embed them, cluster similar requests, score opportunities, and show a Streamlit dashboard.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/init_db.py
python scripts/load_sample_data.py
python scripts/run_pipeline.py
streamlit run src/unmet_demand/dashboard/app.py
```

The dashboard title is **Unmet Demand Intelligence** and displays top scored clusters from `data/sample_posts.jsonl`.

## What The MVP Does

- Stores raw posts, extracted requests, and scored clusters in SQLite.
- Extracts candidate demand signals with regex patterns such as "I wish there was", "why doesn't this exist", and "looking for a tool that".
- Structures each extracted request with problem, desired solution, niche, urgency, emotion, monetization, and an evidence quote.
- Uses `sentence-transformers/all-MiniLM-L6-v2` when available.
- Falls back to scikit-learn TF-IDF embeddings if model loading fails or local model files are unavailable.
- Keeps model loading local-only by default. Set `UNMET_DEMAND_ALLOW_MODEL_DOWNLOAD=1` to allow downloading the embedding model.
- Uses HDBSCAN when installed, otherwise falls back to agglomerative clustering, then DBSCAN.
- Scores opportunities with the requested weighted formula.

## Useful Commands

```bash
python scripts/extract_requests.py
python scripts/cluster_requests.py
python scripts/score_clusters.py
python scripts/import_exported_data.py data/reddit_export.jsonl --source-type reddit
python scripts/review_cluster.py 1 accepted --notes "Promising MVP candidate"
pytest
```

## Data And Database

The default database path is `data/unmet_demand.db`. Override it with:

```bash
export UNMET_DEMAND_DB_PATH=/path/to/unmet_demand.db
```

## Integrations

Exported datasets can be imported without API keys:

```bash
python scripts/import_exported_data.py path/to/export.jsonl --source-type reddit
python scripts/import_exported_data.py path/to/export.jsonl --source-type forum
python scripts/import_exported_data.py path/to/export.jsonl --source-type github
python scripts/import_exported_data.py path/to/export.jsonl --source-type community_qa
```

Supported JSONL fields include `id`, `external_id`, `title`, `body`, `text`, `selftext`, `author`, `created_at`, `url`, and `niche`.

Live Reddit ingestion is available as a small optional adapter in `unmet_demand.ingest.reddit`. Set `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and `REDDIT_USER_AGENT` to use the official Reddit API.

Local LLM enrichment is optional and off by default. To enable an Ollama-compatible local endpoint:

```bash
export UNMET_DEMAND_USE_LOCAL_LLM=1
export UNMET_DEMAND_LOCAL_LLM_URL=http://localhost:11434/api/generate
export UNMET_DEMAND_LOCAL_LLM_MODEL=llama3.2
python scripts/run_pipeline.py
```

## Implemented MVP Features

- Reddit ingestion via exported datasets, plus optional official API adapter.
- Rate-limited adapter base for future API-backed forums, issue trackers, and Q&A sources.
- Optional local LLM enrichment with heuristic fallback.
- Deduplication and source credibility scoring.
- Human review workflow in Streamlit and `scripts/review_cluster.py`.

## Remaining TODO

- Add concrete live adapters for specific forums, GitHub Issues search, and Q&A exports once target sources are chosen.
- Add richer near-duplicate detection using embedding similarity.
- Add durable review history/audit events instead of only storing the current cluster status.
