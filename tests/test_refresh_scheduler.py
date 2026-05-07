import sqlite3

from unmet_demand.db import init_db
from unmet_demand.ingest.scheduler import RefreshJob, record_refresh_run


def test_record_refresh_run(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    job = RefreshJob(name="github-test", source="github", query="godot plugin")

    record_refresh_run(conn, job, "success", records_imported=3)

    row = conn.execute("SELECT job_name, status, records_imported FROM source_refresh_runs").fetchone()
    assert row["job_name"] == "github-test"
    assert row["status"] == "success"
    assert row["records_imported"] == 3
