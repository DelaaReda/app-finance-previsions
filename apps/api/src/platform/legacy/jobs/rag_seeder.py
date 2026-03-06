"""
RAG Seeder Job — alimente le RAG store depuis les snapshots news + forecasts.
Tourne apres chaque ingest news (toutes les 30min via cron).
"""
from __future__ import annotations

import ast
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_src = Path(__file__).resolve().parents[3]  # apps/api/src
for _p in [str(_src), str(_src / "platform" / "legacy"), str(_src / "domains"), str(_src / "services")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_NEWS_FRESHNESS_HOURS = 72


def _parse_tickers(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [str(t).strip().upper() for t in raw if str(t).strip()]
    if isinstance(raw, str):
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list):
                return [str(t).strip().upper() for t in parsed if str(t).strip()]
        except Exception:
            pass
        return [t.strip().upper() for t in raw.strip("[]'\"").split(',') if t.strip()]
    return []


def _load_news_articles() -> List[Dict[str, Any]]:
    path = _src / "platform" / "legacy" / "data" / "news_feed.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        inner = data.get("data", data)
        return inner.get("articles", [])
    except Exception as e:
        logger.error("news load failed: %s", e)
        return []


def _load_forecast_rows() -> List[Dict[str, Any]]:
    path = _src / "platform" / "legacy" / "data" / "forecasts.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        inner = data.get("data", data)
        return inner.get("rows", data.get("rows", []))
    except Exception as e:
        logger.error("forecasts load failed: %s", e)
        return []


def run_rag_seeder(reset: bool = True) -> Dict[str, Any]:
    """Alimente le RAG store: news 72h + forecasts courants."""
    try:
        from research.rag_store import RAGStore
    except Exception as e:
        return {"status": "error", "error": f"RAGStore import failed: {e}"}

    store = RAGStore()
    if reset:
        store.clear()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=_NEWS_FRESHNESS_HOURS)

    # News
    news_seeded = 0
    for a in _load_news_articles():
        if not isinstance(a, dict): continue
        title = a.get("title") or a.get("headline", "")
        summary = a.get("summary", "") or title
        published = a.get("published_at") or a.get("published", "")
        if not title: continue
        if published:
            try:
                pub = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if pub < cutoff: continue
            except Exception: pass
        store.add_news_item({
            "title": title[:200],
            "summary": summary[:500],
            "url": a.get("url", ""),
            "published": published,
            "tickers": _parse_tickers(a.get("tickers", [])),
            "score": float(a.get("score", 0.5) or 0.5),
            "source": a.get("source", ""),
            "sentiment": a.get("sentiment", "neutral"),
        })
        news_seeded += 1

    # Forecasts
    fc_seeded = 0
    last_update = datetime.now(timezone.utc).isoformat()
    for r in _load_forecast_rows():
        if not isinstance(r, dict): continue
        ticker = str(r.get("ticker", "")).upper().strip()
        direction = str(r.get("direction", "flat")).lower()
        conf = float(r.get("confidence", 0.5) or 0.5)
        ret = float(r.get("expected_return", 0) or 0)
        reas = r.get("reasoning", [])
        reasoning = " | ".join(reas[:2]) if isinstance(reas, list) else str(reas)[:200]
        store.add_news_item({
            "title": f"[FORECAST] {ticker} -> {direction.upper()} ({conf:.0%})",
            "summary": (f"Signal IA {ticker}: {direction} conf={conf:.0%} ret={ret:+.2f}%. {reasoning[:300]}"),
            "url": f"backend://forecasts/{ticker}",
            "published": last_update,
            "tickers": [ticker] if ticker else [],
            "score": conf,
            "source": "forecasts_engine",
        })
        fc_seeded += 1

    stats = store.stats()
    return {
        "status": "ok",
        "news_seeded": news_seeded,
        "forecasts_seeded": fc_seeded,
        "rag_total": stats.get("total", 0),
        "timestamp": last_update,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = run_rag_seeder()
    print(json.dumps(result, indent=2, default=str))
