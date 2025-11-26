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

# Dynamic working models (OpenRouter/DeepInfra)
try:
    from agents.g4f_model_watcher import ensure_working_models
except Exception:
    ensure_working_models = None

# Optional LLM judge (econ_llm_agent)
try:
    from analytics.econ_llm_agent import EconomicAnalyst, EconomicInput  # type: ignore
except Exception as e:  # pragma: no cover
    EconomicAnalyst = None  # type: ignore
    EconomicInput = None  # type: ignore
    _LLM_IMPORT_ERROR = e
else:
    _LLM_IMPORT_ERROR = None

# Phase adapter (lightweight summaries)
try:
    from analytics.phases_adapter import build_phase_blocks
except Exception:
    build_phase_blocks = None

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
            # Raw data for prices/macro (re-used for tech/macro features)
            prices_path = backend_root / "data" / "stocks" / "prices.json"
            macro_path = backend_root / "data" / "macro_series.json"
            ownership_path = backend_root / "data" / "ownership_snapshot.json"
            yahoo_cache: Dict[str, Dict[str, Any]] = {}
            judge_features_path = backend_root / "data" / "judge_features.json"

            def _load_judge_features():
                try:
                    return json.loads(judge_features_path.read_text()).get("tickers", {})
                except Exception:
                    return {}

            def _load_prices():
                try:
                    return json.loads(prices_path.read_text()).get("tickers", {})
                except Exception:
                    return {}

            def _load_macro():
                try:
                    return json.loads(macro_path.read_text()).get("series", {})
                except Exception:
                    return {}

            def _load_ownership():
                try:
                    return json.loads(ownership_path.read_text())
                except Exception:
                    return {}

            prices_data = _load_prices()
            macro_series = _load_macro()
            ownership_data = _load_ownership()
            judge_features = _load_judge_features()

            def _yahoo_snapshot(sym: str) -> Dict[str, Any]:
                symu = sym.upper()
                if symu in yahoo_cache:
                    return yahoo_cache[symu]
                if isinstance(ownership_data, dict) and ownership_data.get(symu):
                    yahoo_cache[symu] = ownership_data[symu]
                    return yahoo_cache[symu]
                try:
                    from ingestion.financials_ownership_client import yahoo_snapshot
                except Exception:
                    yahoo_snapshot = None
                if not yahoo_snapshot:
                    return {}
                try:
                    snap = yahoo_snapshot(symu, use_cache=True)
                    if snap:
                        yahoo_cache[symu] = snap
                        return snap
                except Exception:
                    return {}
                return {}

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
                # Prioritize recency then sentiment
                def _ts(a):
                    ts = a.get("timestamp") or a.get("ts") or a.get("published_at")
                    return ts or ""
                rel = sorted(rel, key=lambda a: (_ts(a), a.get("sentiment_score", 0)), reverse=True)
                return rel[:12]

            def _tech_for(sym: str) -> Dict[str, Any]:
                data = prices_data.get(sym) or {}
                pts = data.get("points") or data.get("prices") or []
                if not pts or len(pts) < 5:
                    return {}
                pts = sorted(pts, key=lambda x: x[0])
                closes = [float(p[1]) for p in pts if len(p) >= 2]
                if not closes:
                    return {}
                def sma(window):
                    if len(closes) < window:
                        return None
                    return sum(closes[-window:]) / window
                def vol(window):
                    if len(closes) < window:
                        return None
                    rets = []
                    for i in range(1, window):
                        if closes[-window + i -1] != 0:
                            rets.append((closes[-window + i] - closes[-window + i -1]) / closes[-window + i -1])
                    if not rets:
                        return None
                    avg = sum(rets)/len(rets)
                    var = sum((r-avg)**2 for r in rets)/len(rets)
                    return var**0.5
                def rsi(period=14):
                    if len(closes) <= period:
                        return None
                    gains, losses = 0.0, 0.0
                    for i in range(len(closes)-period, len(closes)-1):
                        diff = closes[i+1]-closes[i]
                        if diff > 0: gains += diff
                        else: losses -= diff
                    if gains == 0 and losses == 0:
                        return 50.0
                    if losses == 0:
                        return 100.0
                    rs = gains/max(1e-9, losses)
                    return 100 - (100/(1+rs))
                last_close = closes[-1]
                sma20 = sma(20)
                sma50 = sma(50)
                vol20 = vol(20)
                return {
                    "rsi": round(rsi(14), 2) if rsi(14) is not None else None,
                    "sma20_vs_price": round((sma20 - last_close)/last_close, 4) if sma20 else None,
                    "sma50_vs_price": round((sma50 - last_close)/last_close, 4) if sma50 else None,
                    "vol20": round(vol20, 4) if vol20 is not None else None,
                    "volume": data.get("volume"),
                    "last_price": last_close,
                }

            def _macro_snapshot():
                out = {}
                def last_val(key):
                    series = macro_series.get(key, {}).get("observations") or []
                    return series[-1]["value"] if series else None
                out["vix"] = last_val("VIXCLS")
                out["us10y"] = last_val("DGS10")
                out["cpi_last"] = last_val("CPIAUCSL")
                out["cpi_last_date"] = (macro_series.get("CPIAUCSL", {}).get("observations") or [{}])[-1].get("date") if macro_series.get("CPIAUCSL") else None
                # DXY (broad trade-weighted USD) si dispo
                for key in ("DTWEXBGS", "DTWEXAFEGS", "DXY"):
                    val = last_val(key)
                    if val is not None:
                        out["dxy"] = val
                        out["dxy_series"] = key
                        break
                return out

            def _ownership_for(sym: str) -> Dict[str, Any]:
                snap = ownership_data.get(sym.upper()) if isinstance(ownership_data, dict) else None
                if not snap:
                    snap = _yahoo_snapshot(sym)
                if snap and isinstance(snap, dict):
                    return {
                        "sector": snap.get("sector") or snap.get("industry"),
                        "industry": snap.get("industry"),
                        "marketCap": snap.get("marketCap") or snap.get("mktCap"),
                        "pe": snap.get("trailingPE") or snap.get("pe"),
                        "beta": snap.get("beta"),
                        "avgVolume": snap.get("averageVolume") or snap.get("avgVolume"),
                    }
                return {}

            def _judge_feature_for(sym: str) -> Dict[str, Any]:
                return judge_features.get(sym.upper()) if isinstance(judge_features, dict) else {}

            macro_ctx = _macro_snapshot()

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

            # Use the same model selection logic as econ_llm_agent (power list no-auth) with dynamic watcher
            os.environ.pop("ECON_AGENT_MODELS", None)
            os.environ.pop("ECON_AGENT_DYNAMIC_MODELS", None)
            candidate_models: Optional[List[str]] = None
            if ensure_working_models:
                try:
                    candidate_models = ensure_working_models(limit=6, max_age_hours=1, min_ok=1)
                except Exception:
                    candidate_models = None
            # Allow a quick-test override via env (skip heavy models if needed)
            test_mode = os.getenv("JUDGE_TEST_MODE", "false").lower() in ("1", "true", "yes")
            agent = EconomicAnalyst(
                model_candidates=candidate_models,
                timeout=120,           # 120s par appel LLM
                retries_per_model=1,
                char_budget=800,
            )
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

            sem = asyncio.Semaphore(3)  # allow limited parallelism

            async def _process_row(r):
                async with sem:
                    sym = (r.get("ticker") or r.get("symbol") or "").upper()
                    if not sym:
                        return None
                    base_conf = float(r.get("confidence", 0.5) or 0.0)
                    expected_return = r.get("expected_return")
                    direction = r.get("direction", "neutral")
                    horizon = r.get("horizon") or "1w"

                    enriched = _judge_feature_for(sym) or {}
                    feat = {
                        "ticker": sym,
                        "direction": direction,
                        "expected_return": expected_return,
                        "confidence": base_conf,
                        "horizon": horizon,
                        "model": r.get("model"),
                        "macro_brief": mkt_ctx.get("brief"),
                        "forecasts_bullish": mkt_ctx.get("bullish"),
                        "forecasts_bearish": mkt_ctx.get("bearish"),
                        "forecasts_neutral": mkt_ctx.get("neutral"),
                        "brief_text": _brief_text(),
                        "news_count": len(_news_for(sym)),
                        "tech": enriched.get("tech") or _tech_for(sym),
                        "macro": macro_ctx,
                        "sector": r.get("sector") or _ownership_for(sym).get("sector") or enriched.get("fundamentals", {}).get("sector"),
                        "industry": _ownership_for(sym).get("industry") or enriched.get("fundamentals", {}).get("industry"),
                        "beta": _ownership_for(sym).get("beta") or enriched.get("fundamentals", {}).get("beta"),
                        "marketCap": _ownership_for(sym).get("marketCap") or enriched.get("fundamentals", {}).get("marketCap"),
                        "pe": _ownership_for(sym).get("pe") or enriched.get("fundamentals", {}).get("pe"),
                        "avgVolume": _ownership_for(sym).get("avgVolume") or enriched.get("fundamentals", {}).get("avgVolume"),
                        "fundamentals": enriched.get("fundamentals", {}),
                        "peer_signals": r.get("peer_signals"),
                    }

                    news_items = _news_for(sym)[:5]  # limiter le volume envoyé au LLM
                    news_headlines = [
                        {
                            "title": n.get("title") or n.get("headline"),
                            "sent": n.get("sentiment_score"),
                            "ts": n.get("timestamp") or n.get("ts") or n.get("published_at"),
                            "source": n.get("source"),
                        }
                        for n in news_items[:10]
                        if n.get("title") or n.get("headline")
                    ]

                    question = (
                        f"Verdict structuré pour {sym} (horizon {horizon}). "
                        "Donne un texte synthèse puis UNE seule ligne JSON finale avec les clés "
                        "summary, scenarios, risks, impacts, actions, confidence, data_needed (liste courte), "
                        "ET une clé phase_scores avec les scores numeric (fundamental, technical, macro, sentiment, fusion). "
                        "Utilise et cite les blocs phases (fundamental/technical/macro/sentiment/fusion) et leurs scores dans la synthèse et la ligne JSON. "
                        "Signale explicitement quelles données supplémentaires seraient utiles si elles manquent."
                    )
                    phase_blocks = {}
                    if build_phase_blocks:
                        phase_features = dict(enriched)
                        phase_features.setdefault("fundamentals", enriched.get("fundamentals", {}))
                        phase_features.setdefault("tech", enriched.get("tech") or _tech_for(sym))
                        phase_blocks = build_phase_blocks(
                            sym,
                            phase_features,
                            macro_ctx,
                            news_items,
                        ) or {}
                    payload = {
                        "question": question,
                        "features": feat,
                        "phases": phase_blocks or None,
                        "news": news_items,
                        "attachments": news_headlines or None,
                        "locale": "fr-FR",
                        "meta": {"source": "judge_route", "ticker": sym},
                    }

                    # Call LLM in a worker thread to avoid nested event-loop issues (single-model analyze)
                    def _run_agent():
                        ein = EconomicInput(**payload)
                        res = agent.analyze(ein)
                        return res

                    try:
                        # Timeout global pour le juge (5 minutes max) — conserve 300s
                        res = await asyncio.wait_for(asyncio.to_thread(_run_agent), timeout=300)
                    except asyncio.TimeoutError:
                        res = {"ok": False, "error": "timeout", "answer": ""}
                    except Exception as e:
                        res = {"ok": False, "error": f"{type(e).__name__}: {e}", "answer": ""}
                    verdict_text = f"{sym}: {direction} (conf {base_conf:.2f})"
                    parsed = None
                    model_used = None
                    full_answer = None
                    meta = None
                    if res.get("ok"):
                        full_answer = res.get("answer")
                        verdict_text = full_answer or verdict_text
                        parsed = res.get("parsed")
                        model_used = res.get("model")
                        if parsed and isinstance(parsed, dict) and parsed.get("confidence") is not None:
                            base_conf = float(parsed.get("confidence"))
                    else:
                        full_answer = res.get("answer") or res.get("error") or verdict_text
                    parsed = parsed if isinstance(parsed, dict) else _parse_analysis(full_answer or verdict_text)
                    if isinstance(parsed, dict) and parsed.get("confidence") is None:
                        parsed["confidence"] = base_conf
                    if isinstance(parsed, dict) and phase_blocks:
                        parsed.setdefault("phase_scores", {
                            k: (v.get("score") if isinstance(v, dict) else None)
                            for k, v in phase_blocks.items()
                        })
                    if not isinstance(parsed, dict):
                        parsed = {}

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

                    return {
                        "ticker": sym,
                        "verdict": verdict_text,
                        "confidence": base_conf,
                        "expected_return": expected_return,
                        "risk_level": "medium",
                        "reasoning": parsed.get("summary") if isinstance(parsed, dict) else None,
                        "analysis": parsed if isinstance(parsed, dict) else {"summary": [verdict_text]},
                        "phases": phase_blocks or None,
                        "phase_scores": {k: (v.get("score") if isinstance(v, dict) else None) for k, v in (phase_blocks or {}).items()} or None,
                        "raw_answer": full_answer or verdict_text,
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "model_version": model_used or "econ_llm_agent",
                        "source": ["judge_route", "forecasts_llm"],
                    }

            tasks = [asyncio.create_task(_process_row(r)) for r in top_rows]
            generated_list = await asyncio.gather(*tasks)
            generated = [g for g in generated_list if g]
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
