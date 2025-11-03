from __future__ import annotations

import pandas as pd
import streamlit as st


def render_timeseries(df: pd.DataFrame, x: str, y: str, title: str) -> None:
    if df is None or df.empty or x not in df.columns or y not in df.columns:
        st.info("Série temporelle indisponible.")
        return
    st.subheader(title)
    st.line_chart(df.set_index(x)[y])

