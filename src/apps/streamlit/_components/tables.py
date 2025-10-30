from __future__ import annotations

import pandas as pd
import streamlit as st


def render_table(df: pd.DataFrame, title: str | None = None) -> None:
    if title:
        st.subheader(title)
    if df is None or df.empty:
        st.info("Aucune donnée disponible.")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)

