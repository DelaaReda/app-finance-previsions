from __future__ import annotations

import streamlit as st

from src.apps.streamlit._components.tables import render_table
from src.apps.streamlit._data.loader import get_partitions_status
from src.apps.streamlit._state import ensure_app_state


st.set_page_config(page_title="Observability — Streamlit Unified", layout="wide")
ensure_app_state()

st.title("🔭 Observability")
st.caption("Dernières partitions détectées par domaine")

df = get_partitions_status()
render_table(df)
