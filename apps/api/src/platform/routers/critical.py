from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

try:
    from ..edge.contracts import edge_enabled
    from ..edge.critical_endpoints import (
        recommendations_degraded as edge_recommendations_degraded,
        recommendations_ok as edge_recommendations_ok,
        stocks_sheet_degraded as edge_stocks_sheet_degraded,
        stocks_sheet_ok as edge_stocks_sheet_ok,
    )
except Exception:  # pragma: no cover
    try:
        from platform.edge.contracts import edge_enabled
        from platform.edge.critical_endpoints import (
            recommendations_degraded as edge_recommendations_degraded,
            recommendations_ok as edge_recommendations_ok,
            stocks_sheet_degraded as edge_stocks_sheet_degraded,
            stocks_sheet_ok as edge_stocks_sheet_ok,
        )
    except Exception:
        edge_enabled = lambda *_args, **_kwargs: False  # type: ignore
        edge_recommendations_ok = lambda data, **_: {"ok": True, "data": data}  # type: ignore
        edge_recommendations_degraded = lambda data, **_: {"ok": True, "data": data}  # type: ignore
        edge_stocks_sheet_ok = lambda data, **_: {"ok": True, "data": data}  # type: ignore
        edge_stocks_sheet_degraded = lambda data, **_: {"ok": True, "data": data}  # type: ignore


EDGE_RECOMMENDATIONS_FLAG = "FC_API_EDGE_RECOMMENDATIONS"
EDGE_STOCKS_FLAG = "FC_API_EDGE_STOCKS"


def _ok(data: Any) -> Dict[str, Any]:
    return {"ok": True, "data": data}


def _fallback_market_context(message: str) -> Dict[str, Any]:
    return {
        "regime": "NORMAL",
        "confidence": 0.0,
        "key_drivers": [],
        "characteristics": {
            "volatility": "medium",
            "sentiment": "neutral",
            "trend": "sideways",
            "momentum": "weak",
            "risk_level": "medium",
        },
        "recommended_layout": {
            "primary_widgets": ["intelligence", "forecasts", "news"],
            "emphasis": "opportunities",
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "note": message,
    }


def _stocks_sheet_fallback_payload(ticker: str, message: str) -> Dict[str, Any]:
    now_iso = datetime.utcnow().isoformat() + "Z"
    symbol = str(ticker or "").upper()
    return {
        "ticker": symbol,
        "company_name": symbol,
        "current_price": None,
        "price_change": None,
        "date": now_iso,
        "fundamentals": {},
        "technical_indicators": {},
        "news_count": 0,
        "news_sentiment": 0.5,
        "trading_levels": {},
        "momentum": {"rsi_level": "neutral", "trend": "neutral"},
        "risk_metrics": {},
        "composite_score": None,
        "score_breakdown": None,
        "alerts": [],
        "analysis": {
            "sentiment": "neutral",
            "outlook": "neutral",
            "recommendation": "hold",
            "target_price": None,
            "stop_loss": None,
        },
        "timeframe_analysis": {
            "short_term": "neutral",
            "medium_term": "neutral",
            "long_term": "neutral",
        },
        "generated_at": now_iso,
        "message": message,
        "source": ["stocks_sheet_route", "fallback"],
    }


def _load_market_context_snapshot_fn():
    try:
        from services.intelligence_service import get_market_context_snapshot
        return get_market_context_snapshot
    except Exception:  # pragma: no cover
        try:
            from src.services.intelligence_service import get_market_context_snapshot  # type: ignore
            return get_market_context_snapshot
        except Exception:
            return None


def create_critical_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/recommendations/daily")
    async def recommendations_daily(
        universe: Optional[List[str]] = Query(None, description="Optional list of tickers to consider"),
        limit: int = Query(3, ge=1, le=50),
    ):
        """Daily recommendations from weekly brief snapshots (never-empty payload)."""
        try:
            from storage.io import load_json

            brief = load_json("brief_weekly") or load_json("brief_weekly.json") or {}
            core = brief.get("data") or brief
            top_signals = core.get("top_signals") or []
            items: List[Dict[str, Any]] = []
            universe_set = {u.upper() for u in (universe or []) if isinstance(u, str) and u.strip()}

            for s in top_signals:
                tkr = (s.get("ticker") or "").upper()
                typ = (s.get("type") or "").upper() or "BULLISH"
                if not tkr:
                    continue
                if universe_set and tkr not in universe_set:
                    continue
                if typ != "BULLISH":
                    continue
                conf = s.get("confidence")
                score = int(round((conf or 0) * 100)) if isinstance(conf, (int, float)) else 0
                risk_level = "LOW" if (conf or 0) >= 0.7 else "MEDIUM" if (conf or 0) >= 0.4 else "HIGH"
                items.append(
                    {
                        "ticker": tkr,
                        "action": "BUY",
                        "score": score,
                        "reasoning": s.get("reasoning") or "Forecasts and market brief indicate positive setup.",
                        "catalysts": [],
                        "risk_level": risk_level,
                        "confidence": float(conf) if conf is not None else 0.0,
                        "supporting_data": {
                            "forecast_confidence": float(conf) if conf is not None else None,
                            "news_sentiment": None,
                            "momentum_score": None,
                            "macro_alignment": None,
                        },
                    }
                )

            items = items[:limit]

            try:
                context_fn = _load_market_context_snapshot_fn()
                if context_fn is None:
                    raise RuntimeError("market_context_snapshot_unavailable")
                context = await run_in_threadpool(context_fn)
                market_ctx = {
                    "regime": context.get("insights", {}).get("market_regime", {}).get("current", "NORMAL"),
                    "summary": context.get("insights", {}).get("summary") or "",
                    "key_drivers": [],
                }
            except Exception:
                mc = _fallback_market_context("Recommendations context")
                market_ctx = {"regime": mc.get("regime", "NORMAL"), "summary": mc.get("summary", ""), "key_drivers": []}

            now_iso = datetime.utcnow().isoformat() + "Z"
            payload = {
                "recommendations": items,
                "market_context": market_ctx,
                "generated_at": now_iso,
                "valid_until": now_iso,
            }
            if edge_enabled(EDGE_RECOMMENDATIONS_FLAG, default=True):
                return edge_recommendations_ok(payload)
            return _ok(payload)
        except Exception as exc:
            now_iso = datetime.utcnow().isoformat() + "Z"
            fallback_payload = {
                "recommendations": [],
                "market_context": {"regime": "NORMAL", "summary": str(exc), "key_drivers": []},
                "generated_at": now_iso,
                "valid_until": now_iso,
            }
            if edge_enabled(EDGE_RECOMMENDATIONS_FLAG, default=True):
                return edge_recommendations_degraded(fallback_payload, detail=str(exc))
            return _ok(fallback_payload)

    @router.get("/api/stocks/{ticker}/sheet")
    async def ticker_sheet(ticker: str):
        """Detailed ticker sheet (Fiches Ticker) with degraded-safe fallback."""
        try:
            from analytics.phase2_technical import compute_indicators
            from core.data_access import get_close_series
            from core.market_data import get_fundamentals, get_price_history
            from research.alerts import alerts_for_ticker
            from research.scoring import calculate_composite_score
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail=f"Missing market data dependencies: {exc}") from exc

        try:
            series = get_close_series(ticker)
            if series is None or series.empty:
                df_prices = get_price_history(ticker, start=None, interval="1d")
                if df_prices is None or df_prices.empty:
                    raise HTTPException(status_code=404, detail=f"No price data for {ticker}")
            else:
                df_prices = pd.DataFrame({"Close": series})
                df_prices.index.name = "Date"

            fundamentals: Dict[str, Any] = {}
            try:
                fundamentals = get_fundamentals(ticker)
            except Exception:
                fundamentals = {
                    "sector": "N/A",
                    "industry": "N/A",
                    "market_cap": "N/A",
                    "pe_ratio": "N/A",
                    "pb_ratio": "N/A",
                    "dividend_yield": "N/A",
                    "beta": "N/A",
                    "eps": "N/A",
                    "revenue": "N/A",
                    "roe": "N/A",
                }

            try:
                df_with_indicators = compute_indicators(df_prices)
                last_row = df_with_indicators.iloc[-1] if len(df_with_indicators) > 0 else {}
                technical_indicators = {
                    "rsi": float(last_row.get("RSI", 0)) if pd.notna(last_row.get("RSI")) else None,
                    "sma20": float(last_row.get("SMA_20", 0)) if pd.notna(last_row.get("SMA_20")) else None,
                    "sma50": float(last_row.get("SMA_50", 0)) if pd.notna(last_row.get("SMA_50")) else None,
                    "sma200": float(last_row.get("SMA_200", 0)) if pd.notna(last_row.get("SMA_200")) else None,
                    "macd": float(last_row.get("MACD", 0)) if pd.notna(last_row.get("MACD")) else None,
                    "macd_signal": float(last_row.get("MACD_Signal", 0)) if pd.notna(last_row.get("MACD_Signal")) else None,
                    "bollinger_upper": float(last_row.get("BB_upper", 0)) if pd.notna(last_row.get("BB_upper")) else None,
                    "bollinger_lower": float(last_row.get("BB_lower", 0)) if pd.notna(last_row.get("BB_lower")) else None,
                    "volume_sma": float(last_row.get("Volume_SMA", 0)) if pd.notna(last_row.get("Volume_SMA")) else None,
                }
            except Exception:
                technical_indicators = {
                    "rsi": None,
                    "sma20": None,
                    "sma50": None,
                    "sma200": None,
                    "macd": None,
                    "macd_signal": None,
                    "bollinger_upper": None,
                    "bollinger_lower": None,
                    "volume_sma": None,
                }

            news_count = 0
            news_sentiment = 0.5
            try:
                try:
                    from services.news_service import get_news_feed  # type: ignore
                except Exception:
                    from src.services.news_service import get_news_feed  # type: ignore
                news_data = get_news_feed(tickers=[ticker], since="7d", score_min=0.0, region="all", limit=50)
                if isinstance(news_data, dict):
                    data_block = news_data.get("data") if isinstance(news_data.get("data"), dict) else news_data
                    if isinstance(data_block, dict):
                        news_count = int(
                            data_block.get("count")
                            or len(data_block.get("articles") or data_block.get("items") or [])
                        )
                    else:
                        news_count = 0
                else:
                    news_count = int(getattr(news_data, "count", 0) or 0)
            except Exception:
                news_count = 0

            last_price = float(df_prices["Close"].iloc[-1]) if "Close" in df_prices.columns else None
            price_change_pct = None
            if len(df_prices) > 1 and "Close" in df_prices.columns:
                prev_close = float(df_prices["Close"].iloc[-2])
                if prev_close != 0:
                    price_change_pct = ((last_price - prev_close) / prev_close) * 100

            volatility = None
            if len(df_prices) > 20 and "Close" in df_prices.columns:
                returns = df_prices["Close"].pct_change().dropna().tail(20)
                if len(returns) > 1:
                    volatility = float(returns.std() * (252 ** 0.5)) * 100

            composite_score = None
            score_breakdown = None
            try:
                comp_score = calculate_composite_score(ticker.upper())
                composite_score = comp_score.get("composite_score")
                score_breakdown = {
                    "macro": comp_score.get("macro_score"),
                    "technical": comp_score.get("technical_score"),
                    "news": comp_score.get("news_score"),
                }
            except Exception:
                pass

            alerts = []
            try:
                alerts = alerts_for_ticker(df_prices, pd.DataFrame(technical_indicators, index=[0]), news_sentiment, ticker.upper())
            except Exception:
                alerts = []

            ticker_sheet = {
                "ticker": ticker.upper(),
                "company_name": ticker.upper(),
                "current_price": last_price,
                "price_change": price_change_pct,
                "date": df_prices.index[-1].isoformat() if not df_prices.empty else None,
                "fundamentals": fundamentals,
                "technical_indicators": technical_indicators,
                "news_count": news_count,
                "news_sentiment": news_sentiment,
                "trading_levels": {
                    "resistance_s1": technical_indicators.get("sma50"),
                    "resistance_s2": technical_indicators.get("sma200"),
                    "support_r1": technical_indicators.get("sma20"),
                    "support_r2": None,
                },
                "momentum": {
                    "rsi_level": (
                        "neutral"
                        if technical_indicators.get("rsi") and 30 <= technical_indicators["rsi"] <= 70
                        else "overbought"
                        if technical_indicators.get("rsi") and technical_indicators["rsi"] > 70
                        else "oversold"
                        if technical_indicators.get("rsi") and technical_indicators["rsi"] < 30
                        else "neutral"
                    ),
                    "trend": (
                        "bullish"
                        if technical_indicators.get("sma20") and last_price and last_price > technical_indicators["sma20"]
                        else "bearish"
                    ),
                },
                "risk_metrics": {
                    "volatility": volatility,
                    "beta": fundamentals.get("beta"),
                    "max_drawdown": None,
                },
                "composite_score": composite_score,
                "score_breakdown": score_breakdown,
                "alerts": alerts,
                "analysis": {
                    "sentiment": "neutral",
                    "outlook": "neutral",
                    "recommendation": "hold",
                    "target_price": None,
                    "stop_loss": None,
                },
                "timeframe_analysis": {
                    "short_term": "neutral",
                    "medium_term": "neutral",
                    "long_term": "neutral",
                },
            }

            if edge_enabled(EDGE_STOCKS_FLAG, default=True):
                return edge_stocks_sheet_ok(ticker_sheet)
            return _ok(ticker_sheet)
        except HTTPException as exc:
            if edge_enabled(EDGE_STOCKS_FLAG, default=True):
                fallback_payload = _stocks_sheet_fallback_payload(
                    ticker=ticker,
                    message=str(exc.detail) if getattr(exc, "detail", None) else "Ticker sheet unavailable",
                )
                return edge_stocks_sheet_degraded(
                    fallback_payload,
                    code="stocks_sheet_http_exception",
                    message="Ticker sheet unavailable, degraded fallback returned.",
                    detail={"status_code": exc.status_code, "detail": str(exc.detail)},
                    source=["stocks_sheet_route", "http_exception"],
                )
            raise
        except Exception as exc:
            if edge_enabled(EDGE_STOCKS_FLAG, default=True):
                fallback_payload = _stocks_sheet_fallback_payload(
                    ticker=ticker,
                    message=f"Error retrieving ticker sheet for {ticker}",
                )
                return edge_stocks_sheet_degraded(
                    fallback_payload,
                    code="stocks_sheet_internal_error",
                    message=f"Error retrieving ticker sheet for {ticker}",
                    detail=str(exc),
                    source=["stocks_sheet_route", "critical_error_fallback"],
                )
            raise HTTPException(status_code=404, detail=f"Error retrieving ticker sheet for {ticker}: {exc}")

    return router
