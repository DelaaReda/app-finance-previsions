from __future__ import annotations

import streamlit as st
from src.apps.streamlit._components.tables import render_table
from src.apps.streamlit._data.loader import get_forecasts
from src.apps.streamlit._state import ensure_app_state


st.set_page_config(page_title="Forecasts — Streamlit Unified", layout="wide")
ensure_app_state()

st.title("📈 Forecasts")
f = st.session_state["filters"]

df = get_forecasts(f.get("watchlist"))
render_table(df, title="Dernières prévisions par ticker")
