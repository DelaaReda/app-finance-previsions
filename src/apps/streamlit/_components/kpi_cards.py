from __future__ import annotations

import streamlit as st


def render_kpis(items: list[tuple[str, str]]) -> None:
    """Render simple KPI row: [(label, value), ...]."""
    if not items:
        st.info("Aucun KPI disponible.")
        return
    cols = st.columns(len(items))
    for (lbl, val), c in zip(items, cols):
        with c:
            st.metric(lbl, val)

