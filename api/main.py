"""
API FastAPI - Copilote Financier
Routes principales exposant les modules Python existants.
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd

# Import des modules existants
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.market_data import get_price_history, get_fundamentals, get_fred_series
from ingestion.finnews import run_pipeline as run_news_pipeline, list_sources
from analytics.phase2_technical import load_prices, compute_indicators, technical_signals
from analytics.phase3_macro import get_us_macro_bundle
from research.scoring import compute_composite_brief  # Nouveau module à créer
from research.rag_store import RAGStore  # Nouveau module à créer

# ============================================================================
# APP CONFIG
# ============================================================================
app = FastAPI(
    title="Finance Copilot API",
    description="API pour le copilote financier personnel",
    version="0.1.0"
)

# CORS pour webapp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAG Store singleton
rag_store = RAGStore()

# ============================================================================
# MODELS
# ============================================================================
class CopilotRequest(BaseModel):
    """Requête pour le Copilot."""
    question: str
    scope: Optional[Dict[str, Any]] = None
    tickers: Optional[List[str]] = None
    horizon: Optional[str] = "1w"

class CopilotResponse(BaseModel):
    """Réponse du Copilot."""
    answer: str
    citations: List[Dict[str, Any]]
    generated_at: str

# ============================================================================
# UTILS
# ============================================================================
def df_to_timeseries(df: pd.DataFrame, value_col: str = "value") -> List[Dict]:
    """Convertit DataFrame pandas en liste [{t, v}]."""
    if df.empty:
        return []
    result = []
    for idx, row in df.iterrows():
        result.append({
            "t": idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
            "v": float(row[value_col]) if pd.notna(row[value_col]) else None
        })
    return result

def df_to_ohlcv(df: pd.DataFrame) -> List[Dict]:
    """Convertit DataFrame OHLCV en liste [{t, o, h, l, c, v}]."""
    if df.empty:
        return []
    result = []
    for idx, row in df.iterrows():
        result.append({
            "t": idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
            "o": float(row.get("Open", 0)) if pd.notna(row.get("Open")) else None,
            "h": float(row.get("High", 0)) if pd.notna(row.get("High")) else None,
            "l": float(row.get("Low", 0)) if pd.notna(row.get("Low")) else None,
            "c": float(row.get("Close", 0)) if pd.notna(row.get("Close")) else None,
            "v": float(row.get("Volume", 0)) if pd.notna(row.get("Volume")) else None,
        })
    return result

# ============================================================================
# ROUTES - MACRO (Pilier 1)
# ============================================================================
@app.get("/api/macro/series")
async def get_macro_series(
    ids: List[str] = Query(..., description="FRED series IDs"),
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD")
):
    """
    Récupère plusieurs séries macro depuis FRED.
    Exemple: /api/macro/series?ids=CPIAUCSL&ids=VIXCLS&start=2019-01-01
    """
    try:
        result = {}
        for series_id in ids:
            df = get_fred_series(series_id, start=start)
            if df is not None and not df.empty:
                # Calculer YoY si pertinent (série mensuelle)
                if len(df) >= 12:
                    df['yoy'] = df['value'].pct_change(12) * 100
                
                result[series_id] = {
                    "data": df_to_timeseries(df, "value"),
                    "yoy": df_to_timeseries(df, "yoy") if 'yoy' in df.columns else None,
                    "source": "FRED",
                    "generated_at": datetime.utcnow().isoformat()
                }
        
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/macro/bundle")
async def get_macro_bundle():
    """Récupère le bundle macro US complet (snapshot)."""
    try:
        bundle = get_us_macro_bundle()
        return {"ok": True, "data": bundle}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================================================
# ROUTES - STOCKS (Pilier 2)
# ============================================================================
@app.get("/api/stocks/prices")
async def get_stock_prices(
    tickers: List[str] = Query(..., description="Tickers (AAPL, NVDA, etc.)"),
    range: str = Query("1y", description="Range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y"),
    interval: str = Query("1d", description="Interval: 1m, 5m, 1h, 1d, 1wk, 1mo")
):
    """
    Récupère prix + indicateurs techniques pour plusieurs tickers.
    Exemple: /api/stocks/prices?tickers=AAPL&tickers=NVDA&range=1y&interval=1d
    """
    try:
        result = {}
        
        for ticker in tickers:
            # Récupérer historique de prix
            df = get_price_history(ticker, start=None, interval=interval)
            
            if df is None or df.empty:
                result[ticker] = None
                continue
            
            # Calculer indicateurs techniques
            df_with_indicators = compute_indicators(df)
            
            # Extraire dernières valeurs des indicateurs
            last_row = df_with_indicators.iloc[-1] if len(df_with_indicators) > 0 else {}
            
            result[ticker] = {
                "prices": df_to_ohlcv(df_with_indicators),
                "indicators": {
                    "rsi": float(last_row.get("RSI", 0)) if pd.notna(last_row.get("RSI")) else None,
                    "sma_20": float(last_row.get("SMA_20", 0)) if pd.notna(last_row.get("SMA_20")) else None,
                    "sma_50": float(last_row.get("SMA_50", 0)) if pd.notna(last_row.get("SMA_50")) else None,
                    "macd": float(last_row.get("MACD", 0)) if pd.notna(last_row.get("MACD")) else None,
                    "macd_signal": float(last_row.get("MACD_Signal", 0)) if pd.notna(last_row.get("MACD_Signal")) else None,
                },
                "last_price": float(last_row.get("Close", 0)) if pd.notna(last_row.get("Close")) else None,
                "source": "yfinance",
                "generated_at": datetime.utcnow().isoformat()
            }
        
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/stocks/fundamentals/{ticker}")
async def get_stock_fundamentals(ticker: str):
    """Récupère les données fondamentales d'une action."""
    try:
        data = get_fundamentals(ticker)
        return {"ok": True, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================================================
# ROUTES - NEWS (Pilier 3)
# ============================================================================
@app.get("/api/news/feed")
async def get_news_feed(
    tickers: Optional[List[str]] = Query(None, description="Filter by tickers"),
    q: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(50, description="Max items to return"),
    window: str = Query("last_week", description="Time window: last_day, last_week, last_month")
):
    """
    Récupère le flux de news scoré et dédupliqué.
    Exemple: /api/news/feed?tickers=AAPL&limit=20&q=earnings
    """
    try:
        # Run news pipeline
        regions = ["US", "CA", "INTL"]
        tgt_ticker = tickers[0] if tickers and len(tickers) > 0 else None
        
        items = run_news_pipeline(
            regions=regions,
            window=window,
            query=q or "",
            tgt_ticker=tgt_ticker,
            per_source_cap=None,
            limit=limit
        )
        
        # Sérialiser les items
        serialized_items = []
        for item in items:
            serialized_items.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "published": item.get("published", ""),
                "source": item.get("source", ""),
                "summary": item.get("summary", ""),
                "score": item.get("score", 0),
                "importance": item.get("importance", 0),
                "freshness": item.get("freshness", 0),
                "relevance": item.get("relevance", 0),
                "sentiment": item.get("sentiment", None),
                "entities": item.get("entities", []),
                "tickers": item.get("tickers", []),
            })
        
        return {
            "ok": True,
            "data": {
                "items": serialized_items,
                "count": len(serialized_items),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/news/save")
async def save_news_to_memory(item: Dict[str, Any]):
    """Enregistre un item de news dans la mémoire RAG."""
    try:
        rag_store.add_news_item(item)
        return {"ok": True, "message": "Item saved to memory"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================================================
# ROUTES - BRIEF & DASHBOARD
# ============================================================================
@app.get("/api/brief")
async def get_market_brief(
    period: str = Query("weekly", description="daily or weekly"),
    universe: List[str] = Query(["SPY", "QQQ"], description="Tickers universe")
):
    """
    Génère le Market Brief avec scoring composite.
    Retourne Top 3 signaux, Top 3 risques, picks.
    """
    try:
        # Compute composite brief (nouveau module scoring.py)
        brief = compute_composite_brief(period=period, universe=universe)
        
        return {
            "ok": True,
            "data": {
                "top_signals": brief.get("top_signals", []),
                "top_risks": brief.get("top_risks", []),
                "picks": brief.get("picks", []),
                "sources": brief.get("sources", []),
                "generated_at": brief.get("generated_at", datetime.utcnow().isoformat()),
                "period": period,
                "universe": universe
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/dashboard/kpis")
async def get_dashboard_kpis():
    """KPIs pour le dashboard (compatible avec l'existant)."""
    try:
        # Réutiliser la logique existante si disponible
        return {
            "ok": True,
            "data": {
                "last_forecast_dt": None,
                "forecasts_count": 0,
                "tickers": 0,
                "horizons": [],
                "last_macro_dt": None,
                "last_quality_dt": None
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================================================
# ROUTES - TICKER SHEET
# ============================================================================
@app.get("/api/tickers/{ticker}/sheet")
async def get_ticker_sheet(ticker: str):
    """
    Fiche complète d'un ticker : prix, indicateurs, news top 5, niveaux.
    """
    try:
        # 1. Prix + indicateurs
        df = get_price_history(ticker, start=None, interval="1d")
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")
        
        df_with_indicators = compute_indicators(df)
        last_row = df_with_indicators.iloc[-1]
        
        # 2. News top 5
        news_items = run_news_pipeline(
            regions=["US", "CA", "INTL"],
            window="last_week",
            tgt_ticker=ticker,
            limit=5
        )
        
        # 3. Niveaux (SMA, RSI, perf)
        close_prices = df["Close"].dropna()
        perf_1w = ((close_prices.iloc[-1] / close_prices.iloc[-5]) - 1) * 100 if len(close_prices) >= 5 else None
        perf_1m = ((close_prices.iloc[-1] / close_prices.iloc[-21]) - 1) * 100 if len(close_prices) >= 21 else None
        
        return {
            "ok": True,
            "data": {
                "ticker": ticker,
                "overview": {
                    "last_price": float(last_row["Close"]),
                    "change_pct": perf_1w,
                },
                "prices": df_to_ohlcv(df_with_indicators[-90:]),  # 90 derniers jours
                "indicators": {
                    "rsi": float(last_row.get("RSI", 0)) if pd.notna(last_row.get("RSI")) else None,
                    "sma_20": float(last_row.get("SMA_20", 0)) if pd.notna(last_row.get("SMA_20")) else None,
                    "sma_50": float(last_row.get("SMA_50", 0)) if pd.notna(last_row.get("SMA_50")) else None,
                    "macd": float(last_row.get("MACD", 0)) if pd.notna(last_row.get("MACD")) else None,
                },
                "news_top": [
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "published": item.get("published"),
                        "score": item.get("score"),
                    }
                    for item in news_items[:5]
                ],
                "levels": {
                    "sma_20": float(last_row.get("SMA_20", 0)) if pd.notna(last_row.get("SMA_20")) else None,
                    "sma_50": float(last_row.get("SMA_50", 0)) if pd.notna(last_row.get("SMA_50")) else None,
                    "rsi": float(last_row.get("RSI", 0)) if pd.notna(last_row.get("RSI")) else None,
                    "perf_1w": perf_1w,
                    "perf_1m": perf_1m,
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================================================
# ROUTES - COPILOT (Pilier 4 : LLM + RAG)
# ============================================================================
@app.post("/api/copilot/ask")
async def copilot_ask(request: CopilotRequest):
    """
    Q&A avec citations (news + séries).
    Utilise le RAG store pour le contexte.
    """
    try:
        # 1. Rechercher contexte dans RAG
        scope = request.scope or {}
        if request.tickers:
            scope["tickers"] = request.tickers
        
        context_chunks = rag_store.search(scope, top_k=10)
        
        # 2. Composer contexte pour LLM
        context_text = "\n\n".join([
            f"[{c['meta']['type']}] {c['text']} (Source: {c['meta'].get('url', 'N/A')}, Date: {c['meta'].get('date', 'N/A')})"
            for c in context_chunks
        ])
        
        # 3. Générer réponse (placeholder - à brancher sur votre LLM)
        # TODO: Intégrer avec analytics/econ_llm_agent ou research/nlp_enrich
        answer = f"Basé sur {len(context_chunks)} sources disponibles, voici mon analyse de '{request.question}'...\n\n[Réponse à implémenter avec LLM]"
        
        # 4. Extraire citations
        citations = [
            {
                "type": c["meta"]["type"],
                "url": c["meta"].get("url", ""),
                "date": c["meta"].get("date", ""),
                "ticker": c["meta"].get("ticker", ""),
                "excerpt": c["text"][:200] + "..." if len(c["text"]) > 200 else c["text"]
            }
            for c in context_chunks
        ]
        
        return {
            "ok": True,
            "data": {
                "answer": answer,
                "citations": citations,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================================================
# ROUTES - FORECASTS (existant)
# ============================================================================
@app.get("/api/forecasts")
async def get_forecasts(
    asset_type: str = Query("all"),
    horizon: str = Query("all"),
    sort_by: str = Query("score")
):
    """Route existante pour les prévisions."""
    try:
        # TODO: Brancher sur analytics/forecaster.py ou lire parquet
        return {
            "ok": True,
            "data": {
                "rows": [],
                "count": 0,
                "asset_type": asset_type
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================================================
# HEALTH CHECK
# ============================================================================
@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "service": "Finance Copilot API", "version": "0.1.0"}

@app.get("/health")
async def health():
    """Health check détaillé."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "fred": True,  # TODO: vérifier connexion FRED
            "yfinance": True,  # TODO: vérifier yfinance
            "news": True,  # TODO: vérifier sources RSS
            "rag": rag_store is not None
        }
    }

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8050, reload=True)
