"""
Judge API Routes - merged version with options + caching
"""
from datetime import datetime
import json
import logging
import asyncio
import os
from pathlib import Path
import time
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Query, HTTPException

# Ensure nested event loops don't break g4f client
try:
    import nest_asyncio

    nest_asyncio.apply()
except Exception:
    pass

try:
    from src.core.response import ok, err
except Exception:  # pragma: no cover
    def ok(data):
        return {"ok": True, "data": data}

    def err(msg, code=500):
        return {"ok": False, "error": msg, "code": code}


from storage.io import load_json

try:
    from services.cache_layer import load_or_compute
except ImportError:  # pragma: no cover
    def load_or_compute(key, compute_fn, **_):
        return compute_fn()


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

# Optional ML prior
try:
    from analytics.ml_baseline import ml_predict_next_return
except Exception:
    ml_predict_next_return = None

# Phase adapter (lightweight summaries)
try:
    from analytics.phases_adapter import build_phase_blocks
except Exception:
    build_phase_blocks = None

# Judge pipeline helpers (scoring, payload, validation)
try:
    from services.judge_pipeline import (
        score_news,
        build_payload,
        parse_llm_answer,
        validate_llm_response,
        log_metrics,
    )
except Exception:
    score_news = None
    build_payload = None
    parse_llm_answer = None
    validate_llm_response = None
    log_metrics = None

logger = logging.getLogger(__name__)

JUDGE_VERSION = "v3"

router = APIRouter(prefix="/api/judge", tags=["judge"])


@router.get("")
async def get_judge_verdicts(
    limit: int = Query(20, ge=1, le=100, description="Limite de résultats (1-100)"),
    min_confidence: float = Query(
        0.5, ge=0.0, le=1.0, description="Confiance minimum pour inclusion (0.0-1.0)"
    ),
    ticker: Optional[List[str]] = Query(
        None, description="Filtre par ticker (plusieurs autorisés)"
    ),
    sort_by: Optional[str] = Query(
        "confidence",
        description="Tri par: confidence, expected_return, score, risk_level, timestamp",
    ),
    sort_order: Optional[str] = Query("desc", description="Ordre de tri: asc, desc"),
):
    """Get LLM judge verdicts for tickers (never-empty, cached)."""
    try:

        async def compute_judge_verdicts():
            if _LLM_IMPORT_ERROR or not EconomicAnalyst or not EconomicInput:
                raise HTTPException(
                    status_code=500,
                    detail=f"econ_llm_agent unavailable: {_LLM_IMPORT_ERROR}",
                )

            # Base data (forecasts + news + macro/brief snapshot)
            forecasts = load_json("forecasts") or {}
            news_feed = load_json("news_feed") or {}
            brief_daily = load_json("brief_daily") or load_json("brief_weekly") or {}

            backend_root = Path(__file__).resolve().parents[3]

            # Raw data for prices/macro (re-used for tech/macro features)
            prices_path = backend_root / "data" / "stocks" / "prices.json"
            macro_path = backend_root / "data" / "macro_series.json"
            ownership_path = backend_root / "data" / "ownership_snapshot.json"
            judge_features_path = backend_root / "data" / "judge_features.json"

            yahoo_cache: Dict[str, Dict[str, Any]] = {}

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

            rows = (
                forecasts.get("rows")
                or forecasts.get("data", {}).get("rows", [])
                or []
            )
            articles = (
                news_feed.get("articles")
                or news_feed.get("data", {}).get("articles", [])
                or []
            )
            rows_sorted = sorted(
                rows, key=lambda r: r.get("confidence", 0), reverse=True
            )
            top_rows = rows_sorted[: min(limit or 3, 3)]

            def _parse_ts(ts_val):
                if not ts_val:
                    return None
                try:
                    return datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                except Exception:
                    try:
                        return datetime.strptime(ts_val, "%Y-%m-%d")
                    except Exception:
                        return None

            def _score_news_items(
                news_list: List[Dict[str, Any]], cap: int = 5
            ) -> List[Dict[str, Any]]:
                """Rank news by recency then |sentiment|, keep top cap."""
                scored = []
                for n in news_list:
                    ts = (
                        n.get("timestamp")
                        or n.get("ts")
                        or n.get("published_at")
                        or n.get("date")
                    )
                    dt = _parse_ts(ts)
                    sent = (
                        n.get("sentiment_score")
                        or n.get("sent")
                        or n.get("sentiment")
                    )
                    try:
                        sent_abs = abs(float(sent)) if sent is not None else 0.0
                    except Exception:
                        sent_abs = 0.0
                    scored.append((dt, sent_abs, n))
                scored.sort(key=lambda x: ((x[0] or datetime.min), x[1]), reverse=True)
                return [x[2] for x in scored[:cap]]

            # Build global context to avoid “données insuffisantes”
            def _market_context():
                total = len(rows)
                bulls = len(
                    [
                        r
                        for r in rows
                        if str(r.get("direction", "")).lower() == "up"
                    ]
                )
                bears = len(
                    [
                        r
                        for r in rows
                        if str(r.get("direction", "")).lower() == "down"
                    ]
                )
                neutrals = total - bulls - bears
                brief = {}
                data = (
                    brief_daily.get("data")
                    if isinstance(brief_daily, dict)
                    else brief_daily
                )
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
                    a
                    for a in articles
                    if symu in (a.get("tickers") or [])
                    or symu in (a.get("symbols") or [])
                ]
                return _score_news_items(rel, cap=12)

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
                        prev_idx = -window + i - 1
                        curr_idx = -window + i
                        if closes[prev_idx] != 0:
                            rets.append(
                                (closes[curr_idx] - closes[prev_idx])
                                / closes[prev_idx]
                            )
                    if not rets:
                        return None
                    avg = sum(rets) / len(rets)
                    var = sum((r - avg) ** 2 for r in rets) / len(rets)
                    return var**0.5

                def rsi(period=14):
                    if len(closes) <= period:
                        return None
                    gains, losses = 0.0, 0.0
                    for i in range(len(closes) - period, len(closes) - 1):
                        diff = closes[i + 1] - closes[i]
                        if diff > 0:
                            gains += diff
                        else:
                            losses -= diff
                    if gains == 0 and losses == 0:
                        return 50.0
                    if losses == 0:
                        return 100.0
                    rs = gains / max(1e-9, losses)
                    return 100 - (100 / (1 + rs))

                last_close = closes[-1]
                sma20 = sma(20)
                sma50 = sma(50)
                vol20 = vol(20)
                return {
                    "rsi": round(rsi(14), 2) if rsi(14) is not None else None,
                    "sma20_vs_price": round(
                        (sma20 - last_close) / last_close, 4
                    )
                    if sma20
                    else None,
                    "sma50_vs_price": round(
                        (sma50 - last_close) / last_close, 4
                    )
                    if sma50
                    else None,
                    "vol20": round(vol20, 4) if vol20 is not None else None,
                    "volume": data.get("volume"),
                    "last_price": last_close,
                }

            def _macro_snapshot():
                out: Dict[str, Any] = {}

                def last_and_delta(key, win: int = 21):
                    series = macro_series.get(key, {}).get("observations") or []
                    if not series:
                        return None, None
                    vals: List[float] = []
                    for s in series:
                        v = s.get("value")
                        if v is None:
                            continue
                        try:
                            vals.append(float(v))
                        except (TypeError, ValueError):
                            continue
                    if not vals:
                        return None, None
                    last = vals[-1]
                    delta = None
                    if len(vals) > win:
                        prev = vals[-1 - win]
                        if prev not in (None, 0):
                            delta = (last - prev) / prev
                    return last, delta

                out["vix"], out["vix_delta_1m"] = last_and_delta("VIXCLS", 21)
                out["us10y"], out["us10y_delta_1m"] = last_and_delta(
                    "DGS10", 21
                )
                cpi_last, cpi_delta = last_and_delta("CPIAUCSL", 1)
                out["cpi_last"] = cpi_last
                out["cpi_delta_1m"] = cpi_delta
                if macro_series.get("CPIAUCSL"):
                    obs = macro_series.get("CPIAUCSL", {}).get(
                        "observations"
                    ) or [{}]
                    out["cpi_last_date"] = obs[-1].get("date")
                else:
                    out["cpi_last_date"] = None

                # DXY (broad trade-weighted USD) si dispo
                for key in ("DTWEXBGS", "DTWEXAFEGS", "DXY"):
                    val, delta = last_and_delta(key, 21)
                    if val is not None:
                        out["dxy"] = val
                        out["dxy_delta_1m"] = delta
                        out["dxy_series"] = key
                        break

                # Commodities (WTI/Brent/Gold) si présents
                wti, wti_delta = last_and_delta("DCOILWTICO", 21)
                brent, brent_delta = last_and_delta("DCOILBRENTEU", 21)
                gold, gold_delta = last_and_delta("GOLDAMGBD228NLBM", 21)
                if wti is not None:
                    out["wti"] = wti
                    out["wti_delta_1m"] = wti_delta
                if brent is not None:
                    out["brent"] = brent
                    out["brent_delta_1m"] = brent_delta
                if gold is not None:
                    out["gold"] = gold
                    out["gold_delta_1m"] = gold_delta
                return out

            def _ownership_for(sym: str) -> Dict[str, Any]:
                snap = (
                    ownership_data.get(sym.upper())
                    if isinstance(ownership_data, dict)
                    else None
                )
                if not snap:
                    snap = _yahoo_snapshot(sym)
                if snap and isinstance(snap, dict):
                    return {
                        "sector": snap.get("sector") or snap.get("industry"),
                        "industry": snap.get("industry"),
                        "marketCap": snap.get("marketCap")
                        or snap.get("mktCap"),
                        "pe": snap.get("trailingPE") or snap.get("pe"),
                        "beta": snap.get("beta"),
                        "avgVolume": snap.get("averageVolume")
                        or snap.get("avgVolume"),
                    }
                return {}

            def _judge_feature_for(sym: str) -> Dict[str, Any]:
                return (
                    judge_features.get(sym.upper())
                    if isinstance(judge_features, dict)
                    else {}
                )

            macro_ctx = _macro_snapshot()

            def _brief_text():
                b = mkt_ctx.get("brief") or {}
                parts: List[str] = []
                if b.get("summary"):
                    parts.append(str(b.get("summary")))
                if b.get("top_signals"):
                    sigs = [
                        s.get("ticker") or s.get("name")
                        for s in b["top_signals"]
                        if isinstance(s, dict)
                    ]
                    parts.append(
                        f"top_signals: {', '.join([s for s in sigs if s])}"
                    )
                if b.get("top_risks"):
                    risks = [
                        r.get("name") or r.get("ticker")
                        for r in b["top_risks"]
                        if isinstance(r, dict)
                    ]
                    parts.append(
                        f"top_risks: {', '.join([r for r in risks if r])}"
                    )
                if b.get("market_sentiment"):
                    parts.append(f"sentiment: {b.get('market_sentiment')}")
                return " | ".join(parts)

            def _parse_analysis(answer: str) -> Dict[str, Any]:
                """Parse LLM answer: use external parser if dispo, sinon JSON sur la dernière ligne."""
                if not answer:
                    return {}
                # 1) parser dédié si dispo
                if parse_llm_answer:
                    try:
                        parsed = parse_llm_answer(answer)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        pass
                # 2) fallback: dernière ligne JSON
                lines = [l.strip() for l in answer.strip().splitlines() if l.strip()]
                if not lines:
                    return {}
                last_line = lines[-1]
                try:
                    data = json.loads(last_line)
                    if isinstance(data, dict):
                        return data
                except Exception:
                    pass
                return {}

            # Use the same model selection logic as econ_llm_agent (power list no-auth) with dynamic watcher
            os.environ.pop("ECON_AGENT_MODELS", None)
            os.environ.pop("ECON_AGENT_DYNAMIC_MODELS", None)
            candidate_models: Optional[List[str]] = None
            if ensure_working_models:
                try:
                    candidate_models = ensure_working_models(
                        limit=6, max_age_hours=1, min_ok=1
                    )
                except Exception:
                    candidate_models = None

            # Allow a quick-test override via env (skip heavy models if needed)
            test_mode = os.getenv("JUDGE_TEST_MODE", "false").lower() in (
                "1",
                "true",
                "yes",
            )

            agent = EconomicAnalyst(
                model_candidates=candidate_models,
                timeout=120,  # 120s par appel LLM
                retries_per_model=1,
                char_budget=800,
            )

            sem = asyncio.Semaphore(3)  # allow limited parallelism

            async def _process_row(r):
                async with sem:
                    sym = (r.get("ticker") or r.get("symbol") or "").upper()
                    if not sym:
                        return None

                    t_total = time.perf_counter()
                    met = {
                        "news_ms": None,
                        "payload_ms": None,
                        "ml_prior_ms": None,
                        "llm_ms": None,
                        "parse_ms": None,
                        "total_ms": None,
                        "llm_model": None,
                        "llm_provider": None,
                    }

                    base_conf = float(r.get("confidence", 0.5) or 0.0)
                    expected_return = r.get("expected_return")
                    direction = r.get("direction", "neutral")
                    horizon = r.get("horizon") or "1w"

                    # verdict_text doit exister même si on échoue avant l'appel LLM
                    verdict_text = (
                        f"{sym}: {direction} (conf {base_conf:.2f})"
                    )

                    # ML prior
                    ml_prior = None
                    t_ml = time.perf_counter()
                    if ml_predict_next_return:
                        try:
                            pred, conf_ml = ml_predict_next_return(
                                sym,
                                horizon=(
                                    horizon
                                    if horizon in ("1w", "1m", "1y")
                                    else "1m"
                                ),
                            )
                            ml_prior = {
                                "pred_return": pred,
                                "confidence": conf_ml,
                                "horizon": horizon,
                                "source": "ml_baseline",
                            }
                        except Exception:
                            ml_prior = {"error": "ml_baseline_failed"}
                    if ml_prior is None:
                        ml_prior = {"error": "ml_baseline_unavailable"}
                    met["ml_prior_ms"] = (
                        time.perf_counter() - t_ml
                    ) * 1000.0

                    enriched = _judge_feature_for(sym) or {}
                    ownership = _ownership_for(sym)

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
                        "tech": {},
                        "macro": macro_ctx,
                        "sector": r.get("sector")
                        or ownership.get("sector")
                        or enriched.get("fundamentals", {}).get("sector"),
                        "industry": ownership.get("industry")
                        or enriched.get("fundamentals", {}).get("industry"),
                        "beta": ownership.get("beta")
                        or enriched.get("fundamentals", {}).get("beta"),
                        "marketCap": ownership.get("marketCap")
                        or enriched.get("fundamentals", {}).get("marketCap"),
                        "pe": ownership.get("pe")
                        or enriched.get("fundamentals", {}).get("pe"),
                        "avgVolume": ownership.get("avgVolume")
                        or enriched.get("fundamentals", {}).get("avgVolume"),
                        "fundamentals": enriched.get("fundamentals", {}),
                        "peer_signals": r.get("peer_signals"),
                        "ml_prior": ml_prior,
                    }

                    # Enrich tech/fund live (with errors as data_needed hints)
                    try:
                        from services.judge_pipeline import (
                            get_tech_enriched,
                            get_fundamental_minimal,
                        )

                        tech_enriched = get_tech_enriched(
                            sym,
                            judge_features
                            if isinstance(judge_features, dict)
                            else {},
                        )
                        if tech_enriched.get("error"):
                            feat.setdefault("data_needed", []).append(
                                tech_enriched["error"]
                            )
                        else:
                            feat["tech"] = tech_enriched
                        fund_enriched = get_fundamental_minimal(sym)
                        if fund_enriched.get("error"):
                            feat.setdefault("data_needed", []).append(
                                fund_enriched["error"]
                            )
                        else:
                            feat["fundamentals_enriched"] = fund_enriched
                    except Exception as e:
                        feat.setdefault("data_needed", []).append(
                            f"enrichment_failed: {e}"
                        )

                    # News selection
                    t_news = time.perf_counter()
                    news_items = _news_for(sym)[:5]  # limiter le volume
                    met["news_ms"] = (
                        time.perf_counter() - t_news
                    ) * 1000.0
                    news_headlines = [
                        {
                            "title": n.get("title") or n.get("headline"),
                            "sent": n.get("sentiment_score")
                            or n.get("sent")
                            or n.get("sentiment"),
                            "ts": n.get("timestamp")
                            or n.get("ts")
                            or n.get("published_at")
                            or n.get("date"),
                            "source": n.get("source"),
                            "summary": (
                                n.get("summary")
                                or n.get("description")
                                or (n.get("raw_text") or "")
                            )[:100],
                            "tickers": n.get("tickers")
                            or n.get("symbols")
                            or [],
                        }
                        for n in news_items
                        if n.get("title") or n.get("headline")
                    ]

                    question = (
                        f"Verdict structuré pour {sym} (horizon {horizon}). "
                        "Donne un texte synthèse puis UNE seule ligne JSON FINALE (dernière ligne uniquement JSON) avec les clés "
                        "summary, scenarios, risks, impacts, actions, confidence, data_needed (liste courte), "
                        "phase_scores (scores numériques), ml_prior. "
                        "Utilise et cite les blocs phases (fundamental/technical/macro/sentiment/fusion) et leurs scores dans la synthèse et le JSON. "
                        "Si une donnée manque, indique-la dans data_needed. Ne renvoie aucun texte après la ligne JSON finale."
                    )

                    phase_blocks: Dict[str, Any] = {}
                    if build_phase_blocks:
                        phase_features = dict(enriched)
                        phase_features.setdefault(
                            "fundamentals", enriched.get("fundamentals", {})
                        )
                        phase_features.setdefault(
                            "tech", enriched.get("tech") or _tech_for(sym)
                        )
                        phase_blocks = (
                            build_phase_blocks(
                                sym,
                                phase_features,
                                macro_ctx,
                                news_items,
                            )
                            or {}
                        )

                    payload = {
                        "question": question,
                        "features": {
                            **feat,
                            "macro": macro_ctx,
                            "news_count": len(news_items),
                            "phases": phase_blocks or {},
                            "ml_prior": ml_prior,
                        },
                        "phases": phase_blocks or None,
                        "news": news_items,
                        "attachments": news_headlines or None,
                        "locale": "fr-FR",
                        "meta": {
                            "source": "judge_route",
                            "ticker": sym,
                            "ml_prior": ml_prior,
                            "data_timestamps": {
                                "macro": macro_ctx.get("cpi_last_date"),
                            },
                        },
                    }

                    # Validate payload (Pydantic) before LLM
                    if build_payload:
                        try:
                            t_payload = time.perf_counter()
                            _ = build_payload(
                                ticker=sym,
                                features=payload["features"],
                                macro=macro_ctx,
                                news=news_items,
                                attachments=news_headlines,
                                phases=phase_blocks or {},
                                ml_prior=ml_prior,
                                locale="fr-FR",
                            )
                            met["payload_ms"] = (
                                time.perf_counter() - t_payload
                            ) * 1000.0
                        except Exception as e:
                            # On renvoie quand même un verdict minimal
                            return {
                                "ticker": sym,
                                "verdict": verdict_text,
                                "confidence": base_conf,
                                "expected_return": expected_return,
                                "risk_level": "medium",
                                "reasoning": [
                                    f"payload_validation_error: {e}"
                                ],
                                "analysis": {
                                    "error": "payload_validation_error",
                                    "details": str(e),
                                },
                                "phases": phase_blocks or None,
                                "phase_scores": {
                                    k: (
                                        v.get("score")
                                        if isinstance(v, dict)
                                        else None
                                    )
                                    for k, v in (phase_blocks or {}).items()
                                }
                                or None,
                                "ml_prior": ml_prior,
                                "raw_answer": "",
                                "generated_at": datetime.utcnow().isoformat()
                                + "Z",
                                "model_version": "econ_llm_agent",
                                "source": ["judge_route", "forecasts_llm"],
                            }

                    # Call LLM in a worker thread to avoid nested event-loop issues
                    def _run_agent():
                        ein = EconomicInput(**payload)
                        return agent.analyze(ein)

                    try:
                        t_llm = time.perf_counter()
                        # Timeout global pour le juge (5 minutes max)
                        res = await asyncio.wait_for(
                            asyncio.to_thread(_run_agent), timeout=300
                        )
                        met["llm_ms"] = (
                            time.perf_counter() - t_llm
                        ) * 1000.0
                    except asyncio.TimeoutError:
                        res = {"ok": False, "error": "timeout", "answer": ""}
                    except Exception as e:
                        res = {
                            "ok": False,
                            "error": f"{type(e).__name__}: {e}",
                            "answer": "",
                        }

                    parsed: Optional[Dict[str, Any]] = None
                    model_used = None
                    full_answer = None

                    if isinstance(res, dict) and res.get("ok"):
                        full_answer = res.get("answer")
                        verdict_text = full_answer or verdict_text
                        parsed = res.get("parsed")
                        model_used = res.get("model")
                        if (
                            parsed
                            and isinstance(parsed, dict)
                            and parsed.get("confidence") is not None
                        ):
                            base_conf = float(parsed.get("confidence"))
                    else:
                        full_answer = (
                            res.get("answer")
                            if isinstance(res, dict)
                            else None
                        ) or (
                            res.get("error")
                            if isinstance(res, dict)
                            else None
                        ) or verdict_text

                    # Parsing / validation
                    t_parse = time.perf_counter()
                    parsed = (
                        parsed
                        if isinstance(parsed, dict)
                        else _parse_analysis(full_answer or verdict_text)
                    )
                    if isinstance(parsed, dict):
                        if parsed.get("confidence") is None:
                            parsed["confidence"] = base_conf
                        if phase_blocks:
                            parsed.setdefault(
                                "phase_scores",
                                {
                                    k: (
                                        v.get("score")
                                        if isinstance(v, dict)
                                        else None
                                    )
                                    for k, v in phase_blocks.items()
                                },
                            )
                        if ml_prior:
                            parsed["ml_prior"] = ml_prior
                        try:
                            parsed = (
                                validate_llm_response(parsed)
                                if validate_llm_response
                                else parsed
                            )
                        except Exception as e:
                            parsed = {
                                "error": f"llm_validation_error: {e}",
                                "raw": full_answer or verdict_text,
                            }
                    else:
                        parsed = {
                            "error": "json_parse_failed",
                            "raw": full_answer or verdict_text,
                        }
                    met["parse_ms"] = (
                        time.perf_counter() - t_parse
                    ) * 1000.0

                    # Default if parsed vide
                    if not parsed or (
                        isinstance(parsed, dict)
                        and parsed.get("error") == "json_parse_failed"
                    ):
                        fallback_news = _news_for(sym)
                        news_titles = [
                            n.get("title")
                            for n in fallback_news[:3]
                            if n.get("title")
                        ]
                        parsed = {
                            "summary": [verdict_text],
                            "scenarios": [
                                {
                                    "name": "base",
                                    "p": 0.55,
                                    "direction": direction,
                                },
                                {
                                    "name": "alt",
                                    "p": 0.25,
                                    "direction": "flat",
                                },
                                {
                                    "name": "risk",
                                    "p": 0.2,
                                    "direction": "opposite",
                                },
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

                    met["total_ms"] = (
                        time.perf_counter() - t_total
                    ) * 1000.0

                    if log_metrics:
                        try:
                            provider = (
                                res.get("provider_raw")
                                or res.get("provider")
                                if isinstance(res, dict)
                                else None
                            )
                            log_metrics(
                                "judge_metrics",
                                ticker=sym,
                                news_ms=met.get("news_ms"),
                                payload_ms=met.get("payload_ms"),
                                ml_prior_ms=met.get("ml_prior_ms"),
                                llm_ms=met.get("llm_ms"),
                                parse_ms=met.get("parse_ms"),
                                total_ms=met.get("total_ms"),
                                llm_model=model_used,
                                llm_provider=provider,
                            )
                        except Exception:
                            pass

                    return {
                        "ticker": sym,
                        "verdict": verdict_text,
                        "confidence": base_conf,
                        "expected_return": expected_return,
                        "risk_level": "medium",
                        "reasoning": parsed.get("summary")
                        if isinstance(parsed, dict)
                        else None,
                        "analysis": parsed
                        if isinstance(parsed, dict)
                        else {"summary": [verdict_text]},
                        "phases": phase_blocks or None,
                        "phase_scores": {
                            k: (
                                v.get("score")
                                if isinstance(v, dict)
                                else None
                            )
                            for k, v in (phase_blocks or {}).items()
                        }
                        or None,
                        "ml_prior": ml_prior,
                        "raw_answer": full_answer or verdict_text,
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "model_version": model_used or "econ_llm_agent",
                        "source": ["judge_route", "forecasts_llm"],
                    }

            tasks = [asyncio.create_task(_process_row(r)) for r in top_rows]
            generated_list = await asyncio.gather(*tasks)
            verdicts = [g for g in generated_list if g]

            # Filtering and stats
            if ticker:
                ticker_list = [t.upper() for t in ticker]
                verdicts = [
                    v
                    for v in verdicts
                    if v.get("ticker", "").upper() in ticker_list
                ]

            confidence_filtered = [
                v
                for v in verdicts
                if v.get("confidence", 0) >= min_confidence
            ]
            if not confidence_filtered and verdicts:
                confidence_filtered = sorted(
                    verdicts,
                    key=lambda x: x.get("confidence", 0),
                    reverse=True,
                )

            reverse_sort = sort_order != "asc"

            if sort_by == "confidence":
                confidence_filtered.sort(
                    key=lambda x: x.get("confidence", 0),
                    reverse=reverse_sort,
                )
            elif sort_by == "expected_return":
                confidence_filtered.sort(
                    key=lambda x: x.get("expected_return", 0)
                    or 0.0,
                    reverse=reverse_sort,
                )
            elif sort_by == "score":
                confidence_filtered.sort(
                    key=lambda x: x.get("score", x.get("confidence", 0)),
                    reverse=reverse_sort,
                )
            elif sort_by == "risk_level":
                risk_order = {
                    "low": 0,
                    "medium": 1,
                    "high": 2,
                    "critical": 3,
                }

                def _risk_val(v: Dict[str, Any]) -> int:
                    return risk_order.get(v.get("risk_level", "medium"), 1)

                confidence_filtered.sort(
                    key=_risk_val, reverse=reverse_sort
                )
            elif sort_by == "timestamp":
                confidence_filtered.sort(
                    key=lambda x: x.get("generated_at", ""),
                    reverse=reverse_sort,
                )
            else:
                confidence_filtered.sort(
                    key=lambda x: x.get("confidence", 0),
                    reverse=reverse_sort,
                )

            limited_verdicts = confidence_filtered[:limit]
            total_verdicts = len(verdicts)
            high_conf_count = len(
                [
                    v
                    for v in limited_verdicts
                    if v.get("confidence", 0) >= 0.7
                ]
            )
            avg_confidence = (
                sum(v.get("confidence", 0) for v in limited_verdicts)
                / len(limited_verdicts)
                if limited_verdicts
                else 0.0
            )

            now_iso = datetime.utcnow().isoformat() + "Z"

            return {
                "verdicts": limited_verdicts,
                "count": len(limited_verdicts),
                "stats": {
                    "total_verdicts": total_verdicts,
                    "high_confidence_count": high_conf_count,
                    "avg_confidence": avg_confidence,
                    "generated_at": now_iso,
                },
                "filters_applied": {
                    "min_confidence": min_confidence,
                    "tickers": ticker,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "limit": limit,
                },
                "generated_at": now_iso,
                "source": ["judge_route", "forecasts_llm"],
            }

        # Ici on pourrait rebrancher load_or_compute si tu veux du cache :
        # verdicts_data = await load_or_compute("judge_verdicts", compute_judge_verdicts)
        verdicts_data = await compute_judge_verdicts()

        return {
            "ok": True,
            "data": verdicts_data,
            "freshness": verdicts_data.get(
                "generated_at", datetime.utcnow().isoformat() + "Z"
            ),
        }
    except Exception as e:
        logger.error(f"Critical error in /judge endpoint: {str(e)}")
        now_iso = datetime.utcnow().isoformat() + "Z"
        return {
            "ok": True,
            "data": {
                "verdicts": [],
                "count": 0,
                "stats": {
                    "total_verdicts": 0,
                    "high_confidence_count": 0,
                    "avg_confidence": 0.0,
                    "generated_at": now_iso,
                },
                "filters_applied": {
                    "min_confidence": min_confidence,
                    "tickers": ticker,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "limit": limit,
                },
                "generated_at": now_iso,
                "source": [
                    "judge_route",
                    "critical_error_fallback",
                    "merged",
                ],
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
        generated_at = datetime.utcnow().isoformat() + "Z"
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
            "generated_at": generated_at,
            "source": ["judge_options_route", "ui_helper_data", "merged"],
        }
        return {"ok": True, "data": options, "freshness": options["generated_at"]}
    except Exception as e:
        now_iso = datetime.utcnow().isoformat() + "Z"
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
                "generated_at": now_iso,
                "error": str(e),
                "message": "Judge options endpoint failed but fallback returned to maintain never-empty contract",
            },
            "freshness": "error",
        }