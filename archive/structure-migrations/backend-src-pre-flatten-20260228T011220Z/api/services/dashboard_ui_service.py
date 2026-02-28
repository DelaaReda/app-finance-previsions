"""
Dashboard UI service helpers for the V16 frontend.

These helpers are **pure Python** (no FastAPI imports) so they can be
tested directly from scripts, and are then wrapped by the FastAPI
routes in ``routes/dashboard.py``.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

# Ensure backend root is on sys.path so ``storage.io`` works when the
# service is imported from different entrypoints.
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(_BACKEND_ROOT) not in sys.path:
  sys.path.insert(0, str(_BACKEND_ROOT))

try:
  from storage.io import load_json
except ImportError:  # pragma: no cover - defensive fallback
  def load_json(key: str) -> Optional[Dict[str, Any]]:  # type: ignore[override]
    return None


def _safe_pct(value: Optional[float]) -> Optional[float]:
  """Convert a ratio (0-1) to percent if needed, rounded to 2 decimals."""
  if value is None:
    return None
  try:
    v = float(value)
  except (TypeError, ValueError):
    return None
  if v <= 1.0:
    v *= 100.0
  return round(v, 2)


def _load_backtest_summary(key: str = "backtests") -> Dict[str, Any]:
  """
  Load a compact backtest summary used by the UI.

  This reads the cached JSON from ``data/backtests.json`` (via
  ``storage.io.load_json``) and normalises it into a simple structure
  that the frontend can consume.
  """
  data = load_json(key) or {}

  # Some jobs store everything under "results", others at top level.
  results = data.get("results") or data
  metrics = results.get("metrics") or results.get("summary") or {}
  summary = results.get("summary") or {}
  params = results.get("params") or {}

  initial_capital = params.get("initial_capital")
  final_capital = results.get("final_capital") or metrics.get("final_portfolio_value")

  # Compute final capital from total_return_pct if needed.
  total_ret_pct = metrics.get("total_return_pct") or summary.get("total_return_pct")
  if final_capital is None and initial_capital is not None and total_ret_pct is not None:
    try:
      final_capital = float(initial_capital) * (1.0 + float(total_ret_pct) / 100.0)
    except Exception:
      final_capital = None

  win_rate = metrics.get("win_rate") or summary.get("win_rate")
  win_rate_pct = _safe_pct(win_rate)

  total_trades = metrics.get("total_trades") or summary.get("total_trades")
  winning_trades = metrics.get("total_winning_trades") or summary.get("winning_trades")
  losing_trades = metrics.get("total_losing_trades") or summary.get("losing_trades")

  return {
    "initial_capital": initial_capital,
    "final_capital": final_capital,
    "total_return_pct": round(float(total_ret_pct), 2) if total_ret_pct is not None else None,
    "win_rate_pct": win_rate_pct,
    "total_trades": total_trades,
    "winning_trades": winning_trades,
    "losing_trades": losing_trades,
  }


def _load_forecast_summary(key: str = "forecasts") -> Dict[str, Any]:
  """
  Aggregate forecast rows into a compact summary for the hero forecast
  KPI (expected next 30d move + average confidence).
  """
  data = load_json(key) or {}
  rows: List[Dict[str, Any]] = data.get("rows") or []

  if not rows:
    return {
      "avg_expected_return_pct": None,
      "avg_confidence_pct": None,
      "total_forecasts": 0,
    }

  expected_returns: List[float] = []
  confidences: List[float] = []

  for row in rows:
    er = row.get("expected_return")
    cf = row.get("confidence")
    try:
      if er is not None:
        expected_returns.append(float(er))
    except (TypeError, ValueError):
      pass
    try:
      if cf is not None:
        confidences.append(float(cf))
    except (TypeError, ValueError):
      pass

  avg_er = (sum(expected_returns) / len(expected_returns)) if expected_returns else None
  avg_cf = (sum(confidences) / len(confidences)) if confidences else None

  return {
    "avg_expected_return_pct": round(avg_er * 100.0, 2) if avg_er is not None else None,
    "avg_confidence_pct": _safe_pct(avg_cf),
    "total_forecasts": len(rows),
  }


def _load_backtest_metrics(key: str = "backtests") -> Dict[str, Any]:
  """
  Load detailed backtest metrics for the portfolio health widget.

  This reads ``data/backtests.json`` and extracts the key metrics used
  by the UI: Sharpe ratio, win rate, max drawdown and total return.
  """
  data = load_json(key) or {}

  results = data.get("results") or data
  metrics = results.get("metrics") or results.get("summary") or {}
  summary = results.get("summary") or {}

  sharpe = metrics.get("sharpe_ratio")
  win_rate = metrics.get("win_rate") or summary.get("win_rate")
  max_dd = metrics.get("max_drawdown") or summary.get("max_drawdown")
  total_ret_pct = metrics.get("total_return_pct") or summary.get("total_return_pct")

  return {
    "sharpe_ratio": float(sharpe) if isinstance(sharpe, (int, float)) else None,
    "win_rate_pct": _safe_pct(win_rate),
    "max_drawdown_pct": round(float(max_dd), 2) if max_dd is not None else None,
    "total_return_pct": round(float(total_ret_pct), 2) if total_ret_pct is not None else None,
  }


def build_market_drivers_snapshot() -> Dict[str, Any]:
  """
  Build a simple \"what's driving the portfolio\" snapshot.

  We derive contributions from real data:
  - Technical: share of forecasts that are purely ML/technical (all rows)
  - News: average news score (scaled)
  - Macro: presence of macro series + their count
  - Sentiment: share of positive/negative news vs neutral

  The goal is not to be perfect quant-wise but to be 100% basé sur
  des données réelles, sans valeurs codées en dur.
  """
  forecasts = load_json("forecasts") or {}
  news = load_json("news_feed") or {}
  macro = load_json("macro_series") or {}

  rows = forecasts.get("rows") or []
  articles = (news.get("data") or {}).get("articles") or news.get("articles") or []
  series = macro.get("series") or {}

  total_forecasts = len(rows)

  # Confidence / expectation average as proxy for technical driver
  confidences = []
  exp_returns = []
  for r in rows:
    try:
      if r.get("confidence") is not None:
        confidences.append(float(r["confidence"]))
    except (TypeError, ValueError):
      pass
    try:
      if r.get("expected_return") is not None:
        exp_returns.append(float(r["expected_return"]))
    except (TypeError, ValueError):
      pass

  avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
  avg_er = sum(exp_returns) / len(exp_returns) if exp_returns else 0.0

  # News sentiment distribution
  pos = neg = neu = 0
  scores = []
  for a in articles:
    s = (a.get("sentiment") or "").lower()
    if s == "positive":
      pos += 1
    elif s == "negative":
      neg += 1
    else:
      neu += 1
    try:
      if a.get("score") is not None:
        scores.append(float(a["score"]))
    except (TypeError, ValueError):
      pass

  total_news = len(articles)
  avg_score = sum(scores) / len(scores) if scores else 0.0

  # Macro driver: number of series available
  macro_series_count = len(series) if isinstance(series, dict) else 0

  # Build contributions (0‑100, then normalised to 100 total)
  tech_raw = max(0.0, min(100.0, avg_conf * 100.0 + avg_er * 2000.0))
  news_raw = max(0.0, min(100.0, avg_score))
  macro_raw = max(0.0, min(100.0, macro_series_count * 5.0))
  sent_raw = max(0.0, min(100.0, (pos + neg) * 3.0))

  total_raw = tech_raw + news_raw + macro_raw + sent_raw or 1.0

  drivers = [
    {"factor": "Technique", "contribution": round(tech_raw / total_raw * 100.0, 1)},
    {"factor": "Nouvelles", "contribution": round(news_raw / total_raw * 100.0, 1)},
    {"factor": "Macro", "contribution": round(macro_raw / total_raw * 100.0, 1)},
    {"factor": "Sentiment", "contribution": round(sent_raw / total_raw * 100.0, 1)},
  ]

  now = datetime.utcnow().isoformat() + "Z"

  return {
    "drivers": drivers,
    "totals": {
      "forecasts": total_forecasts,
      "news_count": total_news,
      "macro_series": macro_series_count,
      "avg_confidence": round(avg_conf * 100.0, 2),
      "avg_expected_return_pct": round(avg_er * 100.0, 2),
      "avg_news_score": round(avg_score, 2),
      "sentiment_breakdown": {
        "positive": pos,
        "negative": neg,
        "neutral": neu,
      },
    },
    "generated_at": now,
    "source": [
      "dashboard_ui_service",
      "forecasts.json",
      "news_feed.json",
      "macro_series.json",
    ],
  }


def build_news_impact_table(limit: int = 10) -> Dict[str, Any]:
  """
  Build the \"News Impact\" table used in the overview.

  We map real news articles from the cached news feed to a compact
  structure similar to mockData.newsImpact: headline, impact, effect.
  """
  news = load_json("news_feed") or {}
  articles = (news.get("data") or {}).get("articles") or news.get("articles") or []

  rows: List[Dict[str, Any]] = []
  for a in articles[: max(0, limit)]:
    score = a.get("score") or 0.0
    sentiment = (a.get("sentiment") or "").lower()
    impact = float(score)
    # Heuristic effect: map sentiment + score to +/- percentage band
    if sentiment == "positive":
      effect = f"+{round(impact / 20.0, 1)}%"
    elif sentiment == "negative":
      effect = f"-{round(impact / 20.0, 1)}%"
    else:
      effect = "0.0%"

    rows.append(
      {
        "headline": a.get("title") or "",
        "impact": round(impact, 1),
        "effect": effect,
        "time": a.get("published_at") or a.get("published") or "",
        "source": a.get("source") or "",
      }
    )

  now = datetime.utcnow().isoformat() + "Z"

  return {
    "items": rows,
    "count": len(rows),
    "generated_at": now,
    "source": [
      "dashboard_ui_service",
      "news_feed.json",
    ],
  }


def build_performance_snapshot() -> Dict[str, Any]:
  """
  Build the \"Top Stocks\" + \"Opportunities\" snapshot for the
  performance widget in the overview tab.

  Data sources (all réelles):
  - forecasts.json  → direction, expected_return, confidence
  - stocks/portfolio_allocation.json → approximate price via value/weight (proxy)
  - recommendations_daily_default_3.json → convictions/opportunities

  The goal is to provide:
  - top_stocks: [{ symbol, price, change_pct, forecast_pct, confidence_pct }]
  - opportunities: [{ conviction, expected_return_pct, confidence_pct, ticker }]
  """
  forecasts = load_json("forecasts") or {}
  rows: List[Dict[str, Any]] = forecasts.get("rows") or []

  alloc = load_json("stocks/portfolio_allocation") or {}
  holdings = {h.get("symbol"): h for h in (alloc.get("holdings") or [])}

  recos = load_json("recommendations_daily_default_3") or {}
  reco_rows: List[Dict[str, Any]] = recos.get("recommendations") or []

  top_stocks: List[Dict[str, Any]] = []
  for r in rows:
    ticker = r.get("ticker")
    if not ticker:
      continue

    # Use portfolio allocation value as a rough proxy for price (value / 1000)
    h = holdings.get(ticker)
    approx_price = None
    if h is not None:
      try:
        approx_price = float(h.get("value", 0.0)) / 1000.0
      except (TypeError, ValueError):
        approx_price = None

    try:
      er_pct = float(r.get("expected_return") or 0.0) * 100.0
    except (TypeError, ValueError):
      er_pct = 0.0
    try:
      conf_pct = float(r.get("confidence") or 0.0) * 100.0
    except (TypeError, ValueError):
      conf_pct = 0.0

    # Change proxy = expected_return over horizon
    change_pct = er_pct

    top_stocks.append(
      {
        "symbol": ticker,
        "price": round(approx_price, 2) if approx_price is not None else None,
        "change_pct": round(change_pct, 1),
        "forecast_pct": round(er_pct, 1),
        "confidence_pct": round(conf_pct, 1),
      }
    )

  # Sort by absolute expected return descending and keep top 6
  top_stocks.sort(key=lambda s: abs(s.get("forecast_pct") or 0.0), reverse=True)
  top_stocks = top_stocks[:6]

  # Build opportunities from recommendations
  opportunities: List[Dict[str, Any]] = []
  for r in reco_rows:
    ticker = r.get("ticker")
    score = r.get("score") or r.get("confidence") or 0.0
    try:
      conf_pct = float(score) * 100.0
    except (TypeError, ValueError):
      conf_pct = 0.0

    # Map action to conviction label
    action = (r.get("action") or "").upper()
    if action == "BUY":
      conviction = "High"
    elif action == "HOLD":
      conviction = "Medium"
    elif action == "SELL":
      conviction = "Defensive"
    else:
      conviction = "Exploratory"

    # Approx expected return proxy = score * 20
    expected_ret_pct = score * 20.0 if isinstance(score, (int, float)) else 0.0

    opportunities.append(
      {
        "ticker": ticker,
        "conviction": conviction,
        "expected_return_pct": round(expected_ret_pct, 1),
        "confidence_pct": round(conf_pct, 1),
      }
    )

  now = datetime.utcnow().isoformat() + "Z"

  return {
    "top_stocks": top_stocks,
    "opportunities": opportunities,
    "generated_at": now,
    "source": [
      "dashboard_ui_service",
      "forecasts.json",
      "data/stocks/portfolio_allocation.json",
      "recommendations_daily_default_3.json",
    ],
  }


def build_portfolio_summary() -> Dict[str, Any]:
  """
  Build the payload expected by the new V16 hero / Portfolio Summary
  widget in the frontend.

  This function is intentionally independent from FastAPI so it can be
  unit-tested or called from scripts. The HTTP endpoint simply wraps it.
  """
  backtest = _load_backtest_summary()
  forecast = _load_forecast_summary()

  portfolio_value = backtest.get("final_capital") or backtest.get("initial_capital")

  return {
    "portfolio_value": portfolio_value,
    "initial_capital": backtest.get("initial_capital"),
    "total_return_pct": backtest.get("total_return_pct"),
    "win_rate_pct": backtest.get("win_rate_pct"),
    "total_trades": backtest.get("total_trades"),
    "winning_trades": backtest.get("winning_trades"),
    "losing_trades": backtest.get("losing_trades"),
    "forecast_next_30d_pct": forecast.get("avg_expected_return_pct"),
    "forecast_confidence_pct": forecast.get("avg_confidence_pct"),
    "total_forecasts": forecast.get("total_forecasts"),
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "source": [
      "dashboard_ui_service",
      "backtests.json",
      "forecasts.json",
    ],
  }


def load_portfolio_allocation() -> Dict[str, Any]:
  """
  Load portfolio allocation snapshot used by the Portfolio Allocation
  treemap widget and related sector summaries.

  Data is expected to be stored in
  ``data/stocks/portfolio_allocation.json`` and accessed via the
  storage IO layer using the key ``\"stocks/portfolio_allocation\"``.

  The function normalises the structure and enriches it with basic
  aggregates so the frontend can consume it directly without having to
  know about the underlying storage format.
  """
  raw = load_json("stocks/portfolio_allocation") or {}

  holdings = raw.get("holdings") or []
  sectors = raw.get("sectors") or []

  # Compute total value to help the UI compute weights if needed.
  total_value = 0.0
  normalized_holdings: List[Dict[str, Any]] = []
  for h in holdings:
    try:
      value = float(h.get("value", 0.0) or 0.0)
    except (TypeError, ValueError):
      value = 0.0
    total_value += value
    normalized_holdings.append(
      {
        "symbol": h.get("symbol"),
        "name": h.get("name"),
        "sector": h.get("sector"),
        "value": value,
        # Keep naming close to UI expectations (return_pct)
        "return_pct": h.get("return_pct"),
      }
    )

  # Ensure sectors list is well formed and numeric.
  normalized_sectors: List[Dict[str, Any]] = []
  for s in sectors:
    try:
      weight = float(s.get("weight_pct", 0.0) or 0.0)
    except (TypeError, ValueError):
      weight = 0.0
    try:
      change = float(s.get("change_pct", 0.0) or 0.0)
    except (TypeError, ValueError):
      change = 0.0
    normalized_sectors.append(
      {
        "sector": s.get("sector"),
        "weight_pct": round(weight, 2),
        "change_pct": round(change, 2),
      }
    )

  now = datetime.utcnow().isoformat() + "Z"

  return {
    "holdings": normalized_holdings,
    "sectors": normalized_sectors,
    "total_value": round(total_value, 2),
    "generated_at": raw.get("generated_at") or now,
    "source": [
      "dashboard_ui_service",
      "stocks/portfolio_allocation.json",
    ],
  }


def build_portfolio_health() -> Dict[str, Any]:
  """
  Build the payload for the Portfolio Health widget +
  backtest metrics section.

  The goal is to provide a compact health score plus the core risk /
  performance metrics, so the frontend can render the gauge and the
  metrics grid without having to inspect the raw backtest file.
  """
  metrics = _load_backtest_metrics()

  win = metrics.get("win_rate_pct") or 0.0
  total_ret = metrics.get("total_return_pct") or 0.0
  max_dd = metrics.get("max_drawdown_pct") or 0.0

  # Simple heuristic for overall health score [0, 100].
  base = 50.0
  try:
    health = base + min(20.0, win / 2.0) + min(20.0, total_ret / 2.0) - min(20.0, max(0.0, -max_dd))
  except Exception:
    health = base

  overall = int(max(0.0, min(100.0, health)))

  suggestion = "Stabiliser le track record avant d'augmenter le risque."
  if overall >= 80:
    suggestion = "Portfolio robuste, possible d'augmenter légèrement l'exposition."
  elif overall >= 60:
    suggestion = "Santé correcte, surveiller drawdown et concentration."
  elif overall <= 40:
    suggestion = "Réduire le risque et diversifier le portefeuille."

  now = datetime.utcnow().isoformat() + "Z"

  return {
    "portfolio_health": {
      "overall": overall,
      "suggestion": suggestion,
    },
    "backtest_results": {
      "sharpe_ratio": metrics.get("sharpe_ratio"),
      "win_rate_pct": metrics.get("win_rate_pct"),
      "max_drawdown_pct": metrics.get("max_drawdown_pct"),
      "total_return_pct": metrics.get("total_return_pct"),
    },
    "generated_at": now,
    "source": [
      "dashboard_ui_service",
      "backtests.json",
    ],
  }
