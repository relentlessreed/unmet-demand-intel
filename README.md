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
pytest
```

## Data And Database

The default database path is `data/unmet_demand.db`. Override it with:

```bash
export UNMET_DEMAND_DB_PATH=/path/to/unmet_demand.db
```

## TODO

- TODO: Add Reddit ingestion using the official Reddit API or exported datasets.
- TODO: Add rate-limited source adapters for forums, issue trackers, and community Q&A.
- TODO: Add local LLM extraction for richer problem and product-angle summaries.
- TODO: Add deduplication and source credibility scoring.
- TODO: Add human review workflow for accepting/rejecting candidate opportunities.
