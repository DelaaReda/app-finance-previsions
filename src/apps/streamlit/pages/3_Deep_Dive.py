from __future__ import annotations

import streamlit as st
import pandas as pd

from src.apps.streamlit._components.charts import render_timeseries
from src.apps.streamlit._data.loader import get_forecasts
from src.apps.streamlit._state import ensure_app_state


st.set_page_config(page_title="Deep Dive — Streamlit Unified", layout="wide")
ensure_app_state()

st.title("🔬 Deep Dive")
f = st.session_state["filters"]
watch = f.get("watchlist", [])

sel = st.selectbox("Ticker", options=watch if watch else ["<aucun>"])

df = get_forecasts([sel]) if sel and sel != "<aucun>" else pd.DataFrame()
render_timeseries(df, x="ds", y="yhat", title=f"Prévision — {sel}")
