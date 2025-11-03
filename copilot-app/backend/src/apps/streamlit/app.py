from __future__ import annotations

import os
from pathlib import Path
import sys
import streamlit as st

# Ensure repo src/ on sys.path for shared utils
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from src.apps.streamlit._state import ensure_app_state
from src.apps.streamlit._components.filters import render_global_filters


st.set_page_config(
    page_title="Streamlit Unified — Finance",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_app_state()

st.title("⚡ Streamlit Unified — Finance")
st.caption("Skeleton — Sprint-codex-1 (parity with Dash, fast local reads)")

with st.sidebar:
    render_global_filters()
    st.divider()
    st.caption("Pages")
    st.page_link("pages/1_Dashboard.py", label="📊 Dashboard")
    st.page_link("pages/2_Signals.py", label="🔎 Signals")
    st.page_link("pages/3_Deep_Dive.py", label="🔬 Deep Dive")
    st.page_link("pages/4_Forecasts.py", label="📈 Forecasts")
    st.page_link("pages/6_Observability.py", label="🔭 Observability")

st.info(
    "This is a new, separate skeleton app. Canonical UI remains on port 5555 (src/apps/agent_app.py)."
)

st.markdown(
    """
### Welcome

Use the sidebar filters and open a page. This skeleton uses:
- Global state via `st.session_state`
- Cached local reads of latest `dt=*` partitions (see loader)
- Clean empty-states when data is missing
    """
)
