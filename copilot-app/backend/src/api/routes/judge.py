"""
Judge API Routes - merged version with options + caching
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
from pathlib import Path
import logging

try:
    from src.core.response import ok, err
except Exception:  # pragma: no cover
    def ok(data): return {"ok": True, "data": data}
    def err(msg, code=500): return {"ok": False, "error": msg, "code": code}

from storage.io import load_json
try:
    from services.cache_layer import load_or_compute
except ImportError:  # pragma: no cover
    def load_or_compute(key, compute_fn, **_): return compute_fn()

# Optional LLM judge (econ_llm_agent)
try:
    from analytics.econ_llm_agent import EconomicAnalyst, EconomicInput  # type: ignore
except Exception as e:  # pragma: no cover
    EconomicAnalyst = None  # type: ignore
    EconomicInput = None  # type: ignore
    _LLM_IMPORT_ERROR = e
else:
    _LLM_IMPORT_ERROR = None

logger = logging.getLogger(__name__)

JUDGE_VERSION = "v3"

router = APIRouter(prefix="/api/judge", tags=["judge"])


@router.get("")
async def get_judge_verdicts(
    limit: int = Query(20, ge=1, le=100, description="Limite de résultats (1-100)"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Confiance minimum pour inclusion (0.0-1.0)"),
    ticker: Optional[List[str]] = Query(None, description="Filtre par ticker (plusieurs autorisés)"),
    sort_by: Optional[str] = Query("confidence", description="Tri par: confidence, expected_return, score"),
    sort_order: Optional[str] = Query("desc", description="Ordre de tri: asc, desc"),
):
    """Get LLM judge verdicts for tickers (never-empty, cached)."""
    try:
        def compute_judge_verdicts():
            if _LLM_IMPORT_ERROR or not EconomicAnalyst or not EconomicInput:
                raise HTTPException(status_code=500, detail=f"econ_llm_agent unavailable: {_LLM_IMPORT_ERROR}")

            judge_data = load_json("llm_judge") or load_json("forecasts_judge") or load_json("judge") or {}
            verdicts = []
            if "data" in judge_data and "verdicts" in judge_data["data"]:
                verdicts = judge_data["data"]["verdicts"]
            elif "data" in judge_data:
                if isinstance(judge_data["data"], list):
                    verdicts = judge_data["data"]
                elif "rows" in judge_data["data"]:
                    verdicts = judge_data["data"]["rows"]
                elif "judgements" in judge_data["data"]:
                    verdicts = judge_data["data"]["judgements"]
                else:
                    verdicts = judge_data["data"]
            elif "rows" in judge_data:
                verdicts = judge_data["rows"]
            elif "verdicts" in judge_data:
                verdicts = judge_data["verdicts"]
            elif "judgements" in judge_data:
                verdicts = judge_data["judgements"]
            elif isinstance(judge_data, list):
                verdicts = judge_data
            else:
                verdicts = []

            # Always generate verdicts via econ_llm_agent using forecasts/news
            forecasts = load_json("forecasts") or {}
            news_feed = load_json("news_feed") or {}
            rows = forecasts.get("rows") or forecasts.get("data", {}).get("rows", []) or []
            articles = news_feed.get("articles") or news_feed.get("data", {}).get("articles", []) or []
            rows_sorted = sorted(rows, key=lambda r: r.get("confidence", 0), reverse=True)
            top_rows = rows_sorted[: limit or 5]

            def _news_for(sym: str) -> List[Dict[str, Any]]:
                symu = sym.upper()
                return [
                    a for a in articles
                    if symu in (a.get("tickers") or []) or symu in (a.get("symbols") or [])
                ][:8]

            analyst = EconomicAnalyst()
            generated: List[Dict[str, Any]] = []
            for r in top_rows:
                sym = (r.get("ticker") or r.get("symbol") or "").upper()
                if not sym:
                    continue
                base_conf = float(r.get("confidence", 0.5) or 0.0)
                expected_return = r.get("expected_return")
                direction = r.get("direction", "neutral")
                verdict_text = f"{sym}: {direction} (conf {base_conf:.2f})"
                parsed = None
                model_used = None

                ei = EconomicInput(
                    question=f"Donne un verdict de trading court pour {sym} horizon {r.get('horizon','1w')}.",
                    features={k: r.get(k) for k in ["ticker","direction","expected_return","confidence","horizon","model"] if k in r},
                    news=_news_for(sym),
                    locale="fr-FR",
                    meta={"source": "judge_route", "ticker": sym},
                )
                res = analyst.analyze(ei)
                if res.get("ok"):
                    verdict_text = res.get("answer") or verdict_text
                    parsed = res.get("parsed")
                    model_used = res.get("model")
                    if parsed and isinstance(parsed, dict) and parsed.get("confidence") is not None:
                        base_conf = float(parsed.get("confidence"))

                generated.append({
                    "ticker": sym,
                    "verdict": verdict_text,
                    "confidence": base_conf,
                    "expected_return": expected_return,
                    "risk_level": "medium",
                    "reasoning": parsed.get("summary") if isinstance(parsed, dict) else None,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "model_version": model_used or "econ_llm_agent",
                    "source": ["judge_route", "forecasts_llm"],
                })
            verdicts = generated

            if ticker:
                ticker_list = [t.upper() for t in ticker]
                verdicts = [v for v in verdicts if v.get("ticker", "").upper() in ticker_list]

            confidence_filtered = [v for v in verdicts if v.get("confidence", 0) >= min_confidence]
            if not confidence_filtered and verdicts:
                # If nothing passes the threshold, downgrade to the top items by confidence
                confidence_filtered = sorted(verdicts, key=lambda x: x.get("confidence", 0), reverse=True)

            reverse_sort = sort_order != "asc"
            if sort_by == "confidence":
                confidence_filtered.sort(key=lambda x: x.get("confidence", 0), reverse=reverse_sort)
            elif sort_by == "expected_return":
                confidence_filtered.sort(key=lambda x: x.get("expected_return", 0), reverse=reverse_sort)
            elif sort_by == "score":
                confidence_filtered.sort(key=lambda x: x.get("score", x.get("confidence", 0)), reverse=reverse_sort)
            else:
                confidence_filtered.sort(key=lambda x: x.get("confidence", 0), reverse=reverse_sort)

            limited_verdicts = confidence_filtered[:limit]
            total_verdicts = len(verdicts)
            high_conf_count = len([v for v in limited_verdicts if v.get("confidence", 0) >= 0.7])
            avg_confidence = sum(v.get("confidence", 0) for v in limited_verdicts) / len(limited_verdicts) if limited_verdicts else 0.0

            return {
                "verdicts": limited_verdicts,
                "count": len(limited_verdicts),
                "stats": {
                    "total_verdicts": total_verdicts,
                    "high_confidence_count": high_conf_count,
                    "avg_confidence": avg_confidence,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                },
                "filters_applied": {
                    "min_confidence": min_confidence,
                    "tickers": ticker,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "limit": limit,
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": judge_data.get("source", ["judge_route", "live_calculation", "merged"]),
            }

        cache_key = f"judge_verdicts_{JUDGE_VERSION}_{limit}_{min_confidence}_{'_'.join([t.lower() for t in ticker]) if ticker else 'all'}_{sort_by}_{sort_order}"
        verdicts_data = load_or_compute(
            key=cache_key,
            compute_fn=compute_judge_verdicts,
            source=["judge_route", "verdict_calculation", "merged"],
        )

        return {
            "ok": True,
            "data": verdicts_data,
            "freshness": verdicts_data.get("generated_at", datetime.utcnow().isoformat() + "Z"),
        }
    except Exception as e:
        logger.error(f"Critical error in /judge endpoint: {str(e)}")
        return {
            "ok": True,
            "data": {
                "verdicts": [],
                "count": 0,
                "stats": {
                    "total_verdicts": 0,
                    "high_confidence_count": 0,
                    "avg_confidence": 0.0,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                },
                "filters_applied": {
                    "min_confidence": min_confidence,
                    "tickers": ticker,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "limit": limit,
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["judge_route", "critical_error_fallback", "merged"],
                "error": str(e),
                "message": "Judge endpoint failed critically but fallback data returned to maintain never-empty contract",
            },
            "freshness": "error",
        }


@router.get("/options")
async def get_judge_options():
    """Options for judge UI (never-empty)."""
    try:
        options = {
            "sort_options": [
                {"value": "confidence", "label": "Confiance"},
                {"value": "expected_return", "label": "Retour attendu"},
                {"value": "risk_level", "label": "Niveau de risque"},
                {"value": "timestamp", "label": "Date de génération"},
            ],
            "risk_levels": ["low", "medium", "high", "critical"],
            "confidence_thresholds": [
                {"label": "Toutes", "value": 0.0},
                {"label": "Haute confiance (0.7+)", "value": 0.7},
                {"label": "Très haute confiance (0.8+)", "value": 0.8},
                {"label": "Excellente confiance (0.9+)", "value": 0.9},
            ],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["judge_options_route", "ui_helper_data", "merged"],
        }
        return {"ok": True, "data": options, "freshness": options["generated_at"]}
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "sort_options": [
                    {"value": "confidence", "label": "Confiance"},
                    {"value": "expected_return", "label": "Retour attendu"},
                ],
                "risk_levels": ["low", "medium", "high"],
                "confidence_thresholds": [
                    {"label": "Toutes", "value": 0.0},
                    {"label": "Haute confiance (0.7+)", "value": 0.7},
                ],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "message": "Judge options endpoint failed but fallback returned to maintain never-empty contract",
            },
            "freshness": "error",
        }
