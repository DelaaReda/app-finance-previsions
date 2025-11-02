from __future__ import annotations

import os
from datetime import date, timedelta
import streamlit as st


DEFAULT_WATCHLIST = tuple(
    (os.getenv("AF_DEFAULT_WATCHLIST") or "SPY,AAPL,NVDA,BTC-USD,GC=F").split(",")
)


def ensure_app_state() -> None:
    """Initialize global session_state keys if absent."""
    if "filters" not in st.session_state:
        today = date.today()
        st.session_state["filters"] = {
            "watchlist": list(DEFAULT_WATCHLIST),
            "date_start": today - timedelta(days=365),
            "date_end": today,
            "asset_class": "all",
            "min_score": 0.0,
            "search": "",
        }

