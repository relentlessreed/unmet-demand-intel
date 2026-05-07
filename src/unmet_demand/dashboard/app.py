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


def save_review(cluster_id: int, status: str, notes: str) -> None:
    with connect() as conn:
        update_cluster_review(conn, cluster_id=cluster_id, status=status, notes=notes.strip() or None)
    load_clusters.clear()
    load_review_events.clear()


clusters = load_clusters()

if clusters.empty:
    st.info("No scored clusters yet. Run `python scripts/run_pipeline.py` from the repo root.")
    st.stop()

opportunity_tab, review_tab, refresh_tab = st.tabs(["Opportunities", "Review History", "Refresh Runs"])

with opportunity_tab:
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
    runs = load_refresh_runs()
    if runs.empty:
        st.info("No source refresh jobs have run yet.")
    else:
        st.dataframe(
            runs[["started_at", "job_name", "source_kind", "query", "status", "records_imported", "error"]],
            use_container_width=True,
            hide_index=True,
        )
