from pathlib import Path

from unmet_demand.service import bool_env, seed_jobs_from_config
from unmet_demand.db import connect, init_db


def test_bool_env(monkeypatch):
    monkeypatch.setenv("FLAG", "true")
    assert bool_env("FLAG") is True
    monkeypatch.setenv("FLAG", "0")
    assert bool_env("FLAG") is False
    monkeypatch.delenv("FLAG")
    assert bool_env("FLAG", default=True) is True


def test_seed_jobs_from_config(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "test.db"
    config_path = tmp_path / "jobs.json"
    config_path.write_text(
        """
        {
          "jobs": [
            {"name": "github-test", "source": "github", "query": "godot plugin", "limit": 5}
          ]
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("UNMET_DEMAND_DB_PATH", str(db_path))
    init_db(db_path)

    assert seed_jobs_from_config(config_path) == 1
    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM source_refresh_jobs").fetchone()[0] == 1
