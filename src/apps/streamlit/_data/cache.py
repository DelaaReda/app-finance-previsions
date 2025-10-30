from __future__ import annotations

import streamlit as st
from .config import get_config


def cache_data(ttl_seconds: int | None = None):
    cfg = get_config()
    ttl = cfg.cache_ttl_seconds if ttl_seconds is None else ttl_seconds
    return st.cache_data(show_spinner=False, ttl=ttl)


def cache_resource():
    return st.cache_resource(show_spinner=False)

