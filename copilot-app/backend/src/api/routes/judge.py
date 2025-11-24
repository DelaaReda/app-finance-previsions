"""
Judge API Routes - merged version with options + caching
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import sys
from pathlib import Path
import logging
import asyncio
import os
import subprocess

# Ensure nested event loops don't break g4f client
try:
    import nest_asyncio
    nest_asyncio.apply()
except Exception:
    pass

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
        async def compute_judge_verdicts():
            if _LLM_IMPORT_ERROR or not EconomicAnalyst or not EconomicInput:
                raise HTTPException(status_code=500, detail=f"econ_llm_agent unavailable: {_LLM_IMPORT_ERROR}")

            # Base data (forecasts + news + macro/brief snapshot)
            forecasts = load_json("forecasts") or {}
            news_feed = load_json("news_feed") or {}
            brief_daily = load_json("brief_daily") or load_json("brief_weekly") or {}
            backend_root = Path(__file__).resolve().parents[3]

            rows = forecasts.get("rows") or forecasts.get("data", {}).get("rows", []) or []
            articles = news_feed.get("articles") or news_feed.get("data", {}).get("articles", []) or []
            rows_sorted = sorted(rows, key=lambda r: r.get("confidence", 0), reverse=True)
            top_rows = rows_sorted[: min(limit or 3, 3)]

            # Build global context to avoid “données insuffisantes”
            def _market_context():
                total = len(rows)
                bulls = len([r for r in rows if str(r.get("direction", "")).lower() == "up"])
                bears = len([r for r in rows if str(r.get("direction", "")).lower() == "down"])
                neutrals = total - bulls - bears
                brief = {}
                data = brief_daily.get("data") if isinstance(brief_daily, dict) else brief_daily
                if isinstance(data, dict):
                    brief = {
                        "summary": data.get("summary") or data.get("title"),
                        "top_signals": data.get("top_signals"),
                        "top_risks": data.get("top_risks"),
                        "market_sentiment": data.get("market_sentiment"),
                    }
                return {
                    "forecasts_total": total,
                    "bullish": bulls,
                    "bearish": bears,
                    "neutral": neutrals,
                    "brief": brief,
                }

            mkt_ctx = _market_context()

            def _news_for(sym: str) -> List[Dict[str, Any]]:
                symu = sym.upper()
                rel = [
                    a for a in articles
                    if symu in (a.get("tickers") or []) or symu in (a.get("symbols") or [])
                ]
                rel = sorted(rel, key=lambda a: a.get("sentiment_score", 0), reverse=True)
                return rel[:12]

            def _brief_text():
                b = mkt_ctx.get("brief") or {}
                parts = []
                if b.get("summary"):
                    parts.append(str(b.get("summary")))
                if b.get("top_signals"):
                    sigs = [s.get("ticker") or s.get("name") for s in b["top_signals"] if isinstance(s, dict)]
                    parts.append(f"top_signals: {', '.join([s for s in sigs if s])}")
                if b.get("top_risks"):
                    risks = [r.get("name") or r.get("ticker") for r in b["top_risks"] if isinstance(r, dict)]
                    parts.append(f"top_risks: {', '.join([r for r in risks if r])}")
                if b.get("market_sentiment"):
                    parts.append(f"sentiment: {b.get('market_sentiment')}")
                return " | ".join(parts)

            time_limit = 35  # Allow slow g4f responses
            # Use the same model selection logic as econ_llm_agent (power list no-auth)
            os.environ.pop("ECON_AGENT_MODELS", None)
            os.environ.pop("ECON_AGENT_DYNAMIC_MODELS", None)
            generated: List[Dict[str, Any]] = []

            def _parse_analysis(answer: str):
                """Try to extract the JSON line from the LLM answer; fallback to a structured dict."""
                if not answer:
                    return None
                # Try to parse last JSON object in the text
                tail = answer.strip().splitlines()
                for line in reversed(tail):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and {"summary", "scenarios", "risks", "impacts", "actions", "confidence"} <= set(obj.keys()):
                            return obj
                    except Exception:
                        continue
                # Fallback: wrap the text in a minimal structure
                return {
                    "summary": [answer],
                    "scenarios": [],
                    "risks": [],
                    "impacts": {},
                    "actions": [],
                    "confidence": None,
                }

            for r in top_rows:
                sym = (r.get("ticker") or r.get("symbol") or "").upper()
                if not sym:
                    continue
                base_conf = float(r.get("confidence", 0.5) or 0.0)
                expected_return = r.get("expected_return")
                direction = r.get("direction", "neutral")

                # Enrich features to give the LLM context instead of “données insuffisantes”
                feat = {
                    "ticker": sym,
                    "direction": direction,
                    "expected_return": expected_return,
                    "confidence": base_conf,
                    "horizon": r.get("horizon"),
                    "model": r.get("model"),
                    "macro_brief": mkt_ctx.get("brief"),
                    "forecasts_bullish": mkt_ctx.get("bullish"),
                    "forecasts_bearish": mkt_ctx.get("bearish"),
                    "forecasts_neutral": mkt_ctx.get("neutral"),
                    "brief_text": _brief_text(),
                    "news_count": len(_news_for(sym)),
                }

                question = (
                    f"Verdict structuré pour {sym} (horizon {r.get('horizon','1w')}). "
                    "Donne un texte synthèse puis UNE seule ligne JSON finale avec les clés "
                    "summary, scenarios, risks, impacts, actions, confidence."
                )
                payload = {
                    "question": question,
                    "features": feat,
                    "news": _news_for(sym),
                    "locale": "fr-FR",
                    "meta": {"source": "judge_route", "ticker": sym},
                }

                def _run_subprocess():
                    py = sys.executable
                    env = os.environ.copy()
                    env["PYTHONPATH"] = f"{backend_root/'src'}:{backend_root}"
                    script = """
import json, sys
from analytics.econ_llm_agent import EconomicAnalyst, EconomicInput
payload = json.loads(sys.stdin.read())
analyst = EconomicAnalyst()
res = analyst.analyze(EconomicInput(**payload))
print(json.dumps(res))
"""
                    try:
                        proc = subprocess.run(
                            [py, "-c", script],
                            input=json.dumps(payload).encode(),
                            capture_output=True,
                            timeout=time_limit,
                            env=env,
                        )
                        if proc.returncode != 0:
                            return {"ok": False, "error": proc.stderr.decode() or proc.stdout.decode()}
                        return json.loads(proc.stdout.decode() or "{}")
                    except Exception as e:
                        return {"ok": False, "error": str(e)}

                res = await asyncio.to_thread(_run_subprocess)
                verdict_text = f"{sym}: {direction} (conf {base_conf:.2f})"
                parsed = None
                model_used = None
                full_answer = None
                if res.get("ok"):
                    full_answer = res.get("answer")
                    verdict_text = full_answer or verdict_text
                    parsed = res.get("parsed")
                    model_used = res.get("model")
                    if parsed and isinstance(parsed, dict) and parsed.get("confidence") is not None:
                        base_conf = float(parsed.get("confidence"))
                else:
                    full_answer = res.get("answer") or res.get("error") or verdict_text
                # Ensure analysis is always a dict
                parsed = parsed if isinstance(parsed, dict) else _parse_analysis(full_answer or verdict_text)
                if isinstance(parsed, dict) and parsed.get("confidence") is None:
                    parsed["confidence"] = base_conf
                if not isinstance(parsed, dict):
                    parsed = {}

                # If parsed is still empty, synthesize a structured analysis from forecasts/news/brief
                if not parsed:
                    news_items = _news_for(sym)
                    news_titles = [n.get("title") for n in news_items[:3] if n.get("title")]
                    parsed = {
                        "summary": [verdict_text],
                        "scenarios": [
                            {"name": "base", "p": 0.55, "direction": direction},
                            {"name": "alt", "p": 0.25, "direction": "flat"},
                            {"name": "risk", "p": 0.2, "direction": "opposite"},
                        ],
                        "risks": news_titles or ["news sensitivity"],
                        "impacts": {
                            "equity": [f"{sym} {direction}"],
                            "rates": [],
                            "FX": [],
                            "commodities": [],
                        },
                        "actions": [
                            f"Surveiller {sym}, expected_return={expected_return}",
                            "Réviser si news négatives",
                        ],
                        "confidence": base_conf,
                    }

                generated.append({
                    "ticker": sym,
                    "verdict": verdict_text,
                    "confidence": base_conf,
                    "expected_return": expected_return,
                    "risk_level": "medium",
                    "reasoning": parsed.get("summary") if isinstance(parsed, dict) else None,
                    "analysis": parsed if isinstance(parsed, dict) else {"summary": [verdict_text]},
                    "raw_answer": full_answer or verdict_text,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "model_version": model_used or "econ_llm_agent",
                    "source": ["judge_route", "forecasts_llm"],
                })
            verdicts = generated

            # Filtering and stats
            if ticker:
                ticker_list = [t.upper() for t in ticker]
                verdicts = [v for v in verdicts if v.get("ticker", "").upper() in ticker_list]

            confidence_filtered = [v for v in verdicts if v.get("confidence", 0) >= min_confidence]
            if not confidence_filtered and verdicts:
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
                "source": ["judge_route", "forecasts_llm"],
            }

        # Always compute fresh verdicts to ensure real LLM output (no cache reuse)
        verdicts_data = await compute_judge_verdicts()

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

# Backward compatibility export
judge_router = router


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
