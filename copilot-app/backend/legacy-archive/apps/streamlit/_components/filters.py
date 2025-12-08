from __future__ import annotations

import streamlit as st
from .._state import ensure_app_state


def render_global_filters() -> None:
    ensure_app_state()
    f = st.session_state["filters"]
    st.header("Filtres globaux")
    f["watchlist"] = st.multiselect("Watchlist", options=f["watchlist"], default=f["watchlist"]) or f["watchlist"]
    col1, col2 = st.columns(2)
    with col1:
        f["date_start"] = st.date_input("Début", value=f["date_start"])  # type: ignore
    with col2:
        f["date_end"] = st.date_input("Fin", value=f["date_end"])  # type: ignore
    f["asset_class"] = st.selectbox("Classe d'actifs", ["all", "equity", "fx", "crypto", "commodity"], index=0)
    f["min_score"] = float(st.slider("Score min.", -1.0, 1.0, float(f.get("min_score", 0.0)), 0.1))
    f["search"] = st.text_input("Recherche", value=f.get("search", ""))

