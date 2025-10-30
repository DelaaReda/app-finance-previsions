# src/api/main.py
from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

# Modules ajoutés
from core.config import CONFIG
from api.errors import ApiError, api_error_handler, generic_error_handler
from api.health import router as health_router
from core.cache import ttl_cache

# Réutilisation modules existants
from core.market_data import get_fred_series, get_price_history
from ingestion.finnews import run_pipeline as news_run_pipeline
from analytics.indicators_basic import compute_indicators as compute_indicators_basic
from analytics.phase2_technical import compute_indicators, load_prices  # si non dispo: fallback simple
from research.brief_renderer import render_brief_html, render_brief_md
from research.alerts import alerts_for_ticker
# Macro bundle optionnel (si pratique)
try:
    from analytics.phase3_macro import get_us_macro_bundle  # type: ignore
except Exception:
    get_us_macro_bundle = None  # type: ignore

# Colle ajoutée
from research.scoring import build_brief
from research.rag_store import search_chunks, add_news_items, add_series_facts

from .schemas import (
    TimePoint, PricePoint, MacroSeries, StockItem, Indicators,
    NewsItem, BriefResponse, CopilotAskRequest, CopilotAnswer, CopilotCitation
)

app = FastAPI(title="Finance Copilot API", version="0.1.0")

# CORS — adapter pour ton domaine Front
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to your webapp's domain for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------- Helpers ----------
def _env_flag(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "0").strip() not in ("0", "false", "False", "")


def _df_to_time_points(df, value_col: str = None):
    """
    Convertit un DataFrame en liste TimePoint/PricePoint.
    Si value_col est donné -> TimePoint. Sinon assume OHLCV -> PricePoint.
    """
    out = []
    if df is None or getattr(df, "empty", True):
        return out
    if value_col:
        for idx, row in df.iterrows():
            v = float(row[value_col]) if value_col in row else float(row.iloc[0])
            out.append(TimePoint(t=str(idx), v=v))
    else:
        # OHLCV
        for idx, r in df.iterrows():
            out.append(
                PricePoint(
                    t=str(idx),
                    o=float(r.get("Open", r.get("open", r.get("O", 0.0)))),
                    h=float(r.get("High", r.get("high", r.get("H", 0.0)))),
                    l=float(r.get("Low", r.get("low", r.get("L", 0.0)))),
                    c=float(r.get("Close", r.get("close", r.get("C", 0.0)))),
                    v=float(r.get("Volume", r.get("volume", r.get("V", 0.0)))),
                )
            )
    return out


# --------- Endpoints ----------

@app.get("/api/macro/series")
def macro_series(ids: List[str] = Query(...), start: Optional[str] = None, end: Optional[str] = None):
    """
    Retourne des séries FRED/indices au format UI-ready.
    """
    series = []
    for sid in ids:
        df = get_fred_series(sid, start=start)
        points = _df_to_time_points(df, value_col=df.columns[-1] if df is not None and len(df.columns) else None)
        series.append(
            MacroSeries(
                id=sid,
                points=points,
                source="FRED",
                ts=datetime.utcnow().isoformat() + "Z",
                url=f"https://fred.stlouisfed.org/series/{sid}",
            )
        )
    return {"series": [s.dict() for s in series]}


@app.get("/api/stocks/prices")
def stocks_prices(tickers: List[str] = Query(...), period: str = "1y", interval: str = "1d"):
    """
    Retourne OHLCV + indicateurs de base (RSI/SMA20/MACD) pour un ou plusieurs tickers.
    Essaie d'utiliser analytics.phase2_technical si dispo, sinon fallback simple.
    """
    items = []
    for t in tickers:
        # Essayons la pipeline technique complète si elle existe
        try:
            df = load_prices(t, period=period, interval=interval)
            ind_df = compute_indicators(df)
            prices = _df_to_time_points(df)  # OHLCV points
            indi = Indicators(
                rsi=float(ind_df["rsi"].dropna().iloc[-1]) if "rsi" in ind_df else None,
                sma20=float(ind_df["sma20"].dropna().iloc[-1]) if "sma20" in ind_df else None,
                macd=float(ind_df["macd"].dropna().iloc[-1]) if "macd" in ind_df else None,
            )
        except Exception:
            # Fallback minimal
            df = get_price_history(t, interval=interval)
            prices = _df_to_time_points(df)
            indi = Indicators()
        items.append(StockItem(ticker=t, prices=prices, indicators=indi).dict())
    return {"items": items}


@app.get("/api/news/feed")
def news_feed(
    tickers: Optional[List[str]] = Query(None),
    q: Optional[str] = None,
    limit: int = 50,
    regions: Optional[List[str]] = Query(["US", "CA", "INTL"])
):
    """
    RSS scoré (finnews.run_pipeline). Tri desc. par score.
    """
    # Window heuristique: "last_week" si limit>50, sinon "last_48h"
    window = "last_48h" if limit <= 50 else "last_week"
    items = news_run_pipeline(regions=regions, window=window, query=q or "", tgt_ticker=(tickers[0] if tickers else None), limit=limit)
    out = []
    for it in items:
        out.append(
            NewsItem(
                id=it.get("id") or it.get("hash") or it.get("url"),
                title=it.get("title") or "",
                url=it.get("url") or it.get("link") or "",
                source=it.get("source") or "",
                published=str(it.get("published") or ""),
                score=float(it.get("score", 0.0)),
                tickers=it.get("tickers") or None,
                lang=it.get("lang") or None,
            ).dict()
        )
    # Option: alimenter le RAG store
    try:
        add_news_items(out)
    except Exception:
        pass
    return {"items": out}


@app.get("/api/brief")
def market_brief(period: str = "weekly", universe: Optional[List[str]] = Query(None)):
    """
    Score composite Macro(40) + Technique(40) + News(20).
    Renvoie Top3 signaux/risques et picks.
    """
    br = build_brief(period=period, universe=universe or ["SPY", "QQQ", "AAPL", "NVDA", "MSFT"])
    return BriefResponse(brief=br["brief"], generatedAt=br["generatedAt"], sources=br["sources"]).dict()


@app.get("/api/tickers/{ticker}/sheet")
def ticker_sheet(ticker: str, period: str = "6mo", interval: str = "1d"):
    """
    Fiche complète: prix+indicateurs + top 5 news + niveaux simples.
    """
    # prix & indicateurs
    try:
        df = load_prices(ticker, period=period, interval=interval)
        ind_df = compute_indicators(df)
        prices = _df_to_time_points(df)
        indi = Indicators(
            rsi=float(ind_df["rsi"].dropna().iloc[-1]) if "rsi" in ind_df else None,
            sma20=float(ind_df["sma20"].dropna().iloc[-1]) if "sma20" in ind_df else None,
            macd=float(ind_df["macd"].dropna().iloc[-1]) if "macd" in ind_df else None,
        )
    except Exception:
        df = get_price_history(ticker, interval=interval)
        prices = _df_to_time_points(df)
        indi = Indicators()

    # top news
    items = news_run_pipeline(regions=["US", "CA", "INTL"], window="last_week", tgt_ticker=ticker, limit=5)
    news = [
        NewsItem(
            id=it.get("id") or it.get("hash") or it.get("url"),
            title=it.get("title") or "",
            url=it.get("url") or it.get("link") or "",
            source=it.get("source") or "",
            published=str(it.get("published") or ""),
            score=float(it.get("score", 0.0)),
            tickers=it.get("tickers") or None,
            lang=it.get("lang") or None,
        ).dict()
        for it in items
    ]

    # niveaux simples
    last_close = prices[-1].c if prices else None
    levels = {"sma20": indi.sma20, "rsi": indi.rsi, "last_close": last_close}

    return {
        "overview": {"ticker": ticker},
        "prices": [p.dict() for p in prices],
        "indicators": indi.dict(),
        "newsTop": news,
        "levels": levels,
    }


# ---- Copilot: Q&A avec citations (RAG minimal sur news/séries) ----

class _Ask(BaseModel):
    question: str
    scope: Optional[dict] = None


@app.post("/api/copilot/ask")
def copilot_ask(payload: CopilotAskRequest):
    """
    Cherche des chunks pertinents (news + facts séries) puis délègue à nlp_enrich.ask_model si dispo.
    Le cas échéant, renvoie une réponse synthétique locale + citations.
    """
    q = payload.question
    scope = payload.scope or {}

    # Récupérer des chunks (top-K) depuis le store
    chunks = search_chunks(scope, topk=8)

    # Option 1: utiliser ton enrichisseur si présent
    try:
        from research.nlp_enrich import ask_model  # type: ignore
        answer = ask_model(q, chunks)  # attendu: {"text": "...", "citations":[...]} si implémenté
        text = answer.get("text") or answer.get("answer") or ""
        cits_raw = answer.get("citations") or []
    except Exception:
        # Option 2: synthèse locale simple
        # (pas d'appel réseau inattendu; juste concat facts)
        facts = [c["text"] for c in chunks[:5]]
        text = f"Résumé basé sur {len(facts)} éléments:\n- " + "\n- ".join(facts)
        cits_raw = [{"type": c["meta"].get("type", "news"),
                     "ref": c["meta"].get("ref") or c["meta"].get("url") or "",
                     "url": c["meta"].get("url"),
                     "t": c["meta"].get("date")} for c in chunks[:5]]

    citations = [CopilotCitation(**c) for c in cits_raw if isinstance(c, dict)]
    return CopilotAnswer(answer=text, citations=citations).dict()