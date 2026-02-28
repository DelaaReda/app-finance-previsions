"""
Client-facing stocks routes to match frontend expectations.
Implements:
- GET /api/stocks/prices?ticker=SPY&interval=1d&downsample=1000
- GET /api/stocks/universe
- GET /api/stocks/{ticker}
- GET /api/stocks/search?q=AAPL&limit=10
- GET /api/stocks/meta?tickers=SPY,QQQ

Uses precomputed snapshots via storage.io when available.
Never returns null values; returns empty arrays/objects on failure.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from storage.io import load_json
except Exception:  # pragma: no cover - very defensive
    load_json = lambda key: None  # type: ignore

from core.ticker_normalization import normalize_ticker, normalize_tickers

router = APIRouter(tags=["stocks"])


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


@router.get("/stocks/prices")
async def get_stocks_prices(
    ticker: str = Query(..., description="Ticker symbol"),
    interval: str = Query("1d", description="Interval (only 1d supported by snapshot)"),
    downsample: int = Query(1000, ge=10, le=5000, description="Max points"),
):
    normalized_ticker = normalize_ticker(ticker)
    if not normalized_ticker:
        normalized_ticker = ticker.upper()
    data = load_json("stocks/prices") or {}
    tickers = (data.get("tickers") or {}) if isinstance(data, dict) else {}
    entry = tickers.get(normalized_ticker) or tickers.get(ticker)

    points_resp: List[Dict[str, Any]] = []
    if entry and isinstance(entry, dict):
        pts = entry.get("points") or []
        # Convert [ts, value] to objects expected by UI
        if isinstance(pts, list) and pts and isinstance(pts[0], (list, tuple)):
            if downsample and len(pts) > downsample:
                step = max(1, len(pts) // downsample)
                pts = pts[::step]
            points_resp = [{"timestamp": int(ts), "value": float(val)} for ts, val in pts if ts is not None and val is not None]

    payload = {
        "ticker": normalized_ticker,
        "interval": interval,
        "points": points_resp,
        "count": len(points_resp),
        "source": "stocks/prices_snapshot",
        "timestamp": _now(),
    }
    return {"ok": True, "data": payload}


@router.get("/stocks/universe")
async def get_stocks_universe():
    # Try to infer universe from prices snapshot keys
    data = load_json("stocks/prices") or {}
    tickers_map = data.get("tickers") if isinstance(data, dict) else None
    tickers = sorted(list(tickers_map.keys())) if isinstance(tickers_map, dict) else []
    return {"ok": True, "data": {"tickers": normalize_tickers(tickers), "count": len(tickers)}}


@router.get("/stocks/{ticker}")
async def get_ticker_detail(ticker: str):
    normalized_ticker = normalize_ticker(ticker)
    if not normalized_ticker:
        normalized_ticker = ticker.upper()
    # Derive last price from prices snapshot
    data = load_json("stocks/prices") or {}
    tickers = (data.get("tickers") or {}) if isinstance(data, dict) else {}
    entry = tickers.get(normalized_ticker) or tickers.get(ticker)

    last_price = None
    last_ts = None
    if entry and isinstance(entry, dict):
        pts = entry.get("points") or []
        if isinstance(pts, list) and pts:
            ts, val = pts[-1] if isinstance(pts[-1], (list, tuple)) else (None, None)
            last_price = float(val) if val is not None else None
            last_ts = int(ts) if ts is not None else None

    resp = {
        "ticker": normalized_ticker,
        "last_price": last_price,
        "date": _now() if last_ts is None else datetime.utcfromtimestamp(last_ts).isoformat() + "Z",
        "indicators": {"rsi": None, "sma20": None, "macd": None},
        "news_count": 0,
    }
    return {"ok": True, "data": resp}


@router.get("/stocks/search")
async def search_stocks(q: str = Query("", description="Query string"), limit: int = Query(10, ge=1, le=50)):
    # Very basic search over universe list (no mocks)
    data = load_json("stocks/prices") or {}
    tickers_map = data.get("tickers") if isinstance(data, dict) else {}
    universe = normalize_tickers(tickers_map.keys() if isinstance(tickers_map, dict) else [])
    qn = (q or "").strip().upper()
    results: List[Dict[str, Any]] = []
    for t in universe:
        if not qn or qn in t:
            results.append({"ticker": t, "name": t, "changePercent": 0, "change": 0})
        if len(results) >= limit:
            break
    return {"ok": True, "data": {"results": results}}


@router.get("/stocks/meta")
async def stocks_meta(tickers: Optional[str] = Query(None, description="Comma separated tickers")):
    items: List[Dict[str, Any]] = []
    if tickers:
        for t in normalize_tickers(x.strip() for x in tickers.split(",") if x.strip()):
            items.append({"ticker": t})
    return {"ok": True, "data": {"items": items}}
