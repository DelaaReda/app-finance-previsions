from __future__ import annotations

import streamlit as st

from src.apps.streamlit._components.kpi_cards import render_kpis
from src.apps.streamlit._components.tables import render_table
from src.apps.streamlit._data.loader import get_forecasts
from src.apps.streamlit._state import ensure_app_state


st.set_page_config(page_title="Dashboard — Streamlit Unified", layout="wide")
ensure_app_state()

st.title("📊 Dashboard")
f = st.session_state["filters"]

df = get_forecasts(f.get("watchlist"))

# Simple KPIs (placeholder)
kpis = [
    ("Tickers", str(len(f.get("watchlist", [])))),
    ("Rows", str(len(df) if df is not None else 0)),
]
render_kpis(kpis)

render_table(df, title="Dernières prévisions (final.parquet)")
