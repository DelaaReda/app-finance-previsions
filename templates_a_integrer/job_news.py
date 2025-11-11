"""
News ingest: fetch real feeds, compute features/sentiment, and persist.
If fetch fails, keep previous snapshot (never replace with fake).
"""
from __future__ import annotations
from typing import Dict, Any
from backend.storage.base import save_json, load_json

def _fetch_and_process_news() -> Dict[str, Any]:
    # TODO: IMPLEMENT real ingestion:
    # fetch RSS/APIs → dedupe → enrich → sentiment → features
    return {}

def run_news_job() -> Dict[str, Any]:
    prev = load_json("news_feed.json")
    data = _fetch_and_process_news()
    if data:
        save_json(data, "news_feed.json", source="news_pipeline", status="OK")
        return data
    return (prev or {"data": {"articles": []}, "status": "NO_SNAPSHOT"})["data"]
