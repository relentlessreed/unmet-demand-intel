from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from unmet_demand.db import connect
from unmet_demand.ingest.scheduler import RefreshJob, delete_refresh_job, upsert_refresh_job
from unmet_demand.review import update_cluster_review


st.set_page_config(page_title="Unmet Demand Intelligence", layout="wide")
st.title("Unmet Demand Intelligence")


@st.cache_data(ttl=10)
def load_clusters() -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM request_clusters
            ORDER BY opportunity_score DESC, request_count DESC
            """,
            conn,
        )


@st.cache_data(ttl=10)
def load_review_events() -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM review_events
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            conn,
        )


@st.cache_data(ttl=10)
def load_refresh_runs() -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM source_refresh_runs
            ORDER BY started_at DESC, id DESC
            LIMIT 100
            """,
            conn,
        )


@st.cache_data(ttl=10)
def load_refresh_jobs() -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM source_refresh_jobs
            ORDER BY enabled DESC, name
            """,
            conn,
        )


def save_review(cluster_id: int, status: str, notes: str) -> None:
    with connect() as conn:
        update_cluster_review(conn, cluster_id=cluster_id, status=status, notes=notes.strip() or None)
    load_clusters.clear()
    load_review_events.clear()


def save_refresh_job(job: RefreshJob, enabled: bool) -> None:
    with connect() as conn:
        upsert_refresh_job(conn, job, enabled=enabled)
    load_refresh_jobs.clear()


def remove_refresh_job(name: str) -> None:
    with connect() as conn:
        delete_refresh_job(conn, name)
    load_refresh_jobs.clear()


clusters = load_clusters()

opportunity_tab, review_tab, refresh_tab = st.tabs(["Opportunities", "Review History", "Refresh Runs"])

with opportunity_tab:
    if clusters.empty:
        st.info("No scored clusters yet. Run `python scripts/run_pipeline.py` from the repo root.")
    else:
        for _, cluster in clusters.iterrows():
            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    st.subheader(cluster["summary"])
                    st.write(cluster["suggested_product_angle"])
                with right:
                    st.metric("Score", f"{cluster['opportunity_score']:.2f}")
                    st.metric("Requests", int(cluster["request_count"]))

                metric_cols = st.columns(3)
                metric_cols[0].metric("Avg urgency", f"{cluster['avg_urgency']:.1f}/5")
                metric_cols[1].metric("Avg emotion", f"{cluster['avg_emotion']:.1f}/5")
                metric_cols[2].metric("Credibility", f"{cluster['source_credibility_score']:.1f}/5")

                st.caption("Representative evidence")
                for quote in json.loads(cluster["representative_quotes"]):
                    st.write(f"- {quote}")

                review_cols = st.columns([1, 2, 1])
                status_options = ["unreviewed", "accepted", "watchlist", "rejected"]
                current_status = cluster.get("review_status", "unreviewed")
                status = review_cols[0].selectbox(
                    "Review",
                    status_options,
                    index=status_options.index(current_status) if current_status in status_options else 0,
                    key=f"status-{cluster['id']}",
                )
                notes = review_cols[1].text_input("Notes", value=cluster.get("review_notes") or "", key=f"notes-{cluster['id']}")
                if review_cols[2].button("Save", key=f"save-{cluster['id']}"):
                    save_review(int(cluster["id"]), status, notes)
                    st.rerun()

with review_tab:
    events = load_review_events()
    if events.empty:
        st.info("No review history yet.")
    else:
        st.dataframe(
            events[["created_at", "cluster_label", "previous_status", "new_status", "notes", "summary_snapshot"]],
            use_container_width=True,
            hide_index=True,
        )

with refresh_tab:
    jobs = load_refresh_jobs()
    with st.expander("Source Jobs", expanded=jobs.empty):
        with st.form("refresh-job-form"):
            job_cols = st.columns(3)
            name = job_cols[0].text_input("Name", value="github-godot-requests")
            source = job_cols[1].selectbox("Source", ["github", "discourse", "stackexchange"])
            enabled = job_cols[2].checkbox("Enabled", value=True)
            query = st.text_input("Query", value="godot plugin request")
            config_cols = st.columns(4)
            limit = config_cols[0].number_input("Limit", min_value=1, max_value=500, value=50)
            pages = config_cols[1].number_input("Pages", min_value=0, max_value=20, value=0)
            interval = config_cols[2].number_input("Interval minutes", min_value=1, max_value=10080, value=360)
            rpm = config_cols[3].number_input("Requests/min", min_value=0, max_value=600, value=0)
            source_cols = st.columns(4)
            base_url = source_cols[0].text_input("Discourse base URL", value="")
            site = source_cols[1].text_input("Stack Exchange site", value="gamedev")
            retries = source_cols[2].number_input("Retries", min_value=0, max_value=10, value=3)
            backoff = source_cols[3].number_input("Backoff seconds", min_value=0.0, max_value=60.0, value=0.0)
            if st.form_submit_button("Save Job"):
                save_refresh_job(
                    RefreshJob(
                        name=name,
                        source=source,
                        query=query,
                        limit=int(limit),
                        pages=int(pages),
                        interval_minutes=int(interval),
                        base_url=base_url.strip() or None,
                        site=site,
                        requests_per_minute=int(rpm),
                        max_retries=int(retries),
                        backoff_seconds=float(backoff) if backoff else None,
                    ),
                    enabled=enabled,
                )
                st.rerun()

        if not jobs.empty:
            st.dataframe(
                jobs[["enabled", "name", "source", "query", "limit_count", "pages", "interval_minutes", "requests_per_minute", "max_retries", "backoff_seconds"]],
                use_container_width=True,
                hide_index=True,
            )
            delete_name = st.selectbox("Delete job", [""] + jobs["name"].tolist())
            if delete_name and st.button("Delete Selected Job"):
                remove_refresh_job(delete_name)
                st.rerun()

    runs = load_refresh_runs()
    if runs.empty:
        st.info("No source refresh jobs have run yet.")
    else:
        st.dataframe(
            runs[["started_at", "job_name", "source_kind", "query", "status", "records_imported", "error"]],
            use_container_width=True,
            hide_index=True,
        )
