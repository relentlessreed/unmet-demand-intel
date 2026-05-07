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


clusters = load_clusters()

if clusters.empty:
    st.info("No scored clusters yet. Run `python scripts/run_pipeline.py` from the repo root.")
    st.stop()

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
        metric_cols[2].metric("Avg monetization", f"{cluster['avg_monetization']:.1f}/5")

        st.caption("Representative evidence")
        for quote in json.loads(cluster["representative_quotes"]):
            st.write(f"- {quote}")
