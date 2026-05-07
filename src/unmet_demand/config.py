from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "unmet_demand.db"
DEFAULT_SAMPLE_PATH = DATA_DIR / "sample_posts.jsonl"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_db_path() -> Path:
    return Path(os.getenv("UNMET_DEMAND_DB_PATH", str(DEFAULT_DB_PATH)))


def get_embedding_model_name() -> str:
    return os.getenv("UNMET_DEMAND_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def allow_model_download() -> bool:
    return os.getenv("UNMET_DEMAND_ALLOW_MODEL_DOWNLOAD", "").lower() in {"1", "true", "yes"}
