from __future__ import annotations

import streamlit as st

from src.apps.streamlit._components.tables import render_table
from src.apps.streamlit._data.loader import get_forecasts
from src.apps.streamlit._state import ensure_app_state


st.set_page_config(page_title="Signals — Streamlit Unified", layout="wide")
ensure_app_state()

st.title("🔎 Signals")
f = st.session_state["filters"]

df = get_forecasts(f.get("watchlist"))
min_score = float(f.get("min_score", 0.0))
if df is not None and not df.empty and "final_score" in df.columns:
    df = df[df["final_score"] >= min_score]

render_table(df, title="Signaux filtrés")
