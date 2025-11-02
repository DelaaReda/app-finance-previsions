#!/usr/bin/env python3
"""
Job quotidien: ajouter news du jour au RAG.
À exécuter via cron: 0 18 * * * /path/to/.venv/bin/python ops/daily_rag_refresh.py
"""
from datetime import datetime, timedelta
import sys
from pathlib import Path
import os

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

def run_daily_rag_refresh():
    """Add daily news to RAG store."""
    from research.rag_store import RAGStore
    from ingestion.finnews import run_pipeline

    rag = RAGStore()

    # News from today (top 50, score > 0.5)
    items = run_pipeline(
        regions=["US", "CA", "INTL"],
        window="last_day",
        query="",
        tgt_ticker=None,
        limit=50
    )

    added = 0
    for item in items:
        if item.get("score", 0) > 0.5:
            rag.add_news_item(item)
            added += 1

    print(f"✅ Added {added} news items to RAG")
    print(f"📊 RAG stats: {rag.stats()}")
    
    return added

if __name__ == "__main__":
    print(f"Running daily RAG refresh: {datetime.now().isoformat()}")
    try:
        count = run_daily_rag_refresh()
        print(f"Daily RAG refresh completed. Added {count} items.")
    except Exception as e:
        print(f"Error during daily RAG refresh: {e}")
        sys.exit(1)