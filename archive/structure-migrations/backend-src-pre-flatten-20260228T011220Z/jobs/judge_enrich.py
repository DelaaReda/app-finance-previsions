"""
Job: Enrich judge data with real market/fundamentals (yfinance)
Fetches OHLCV + fundamentals for tickers in forecasts.json and writes data/judge_features.json
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FORECASTS_PATH = DATA_DIR / "forecasts.json"
OUTPUT_PATH = DATA_DIR / "judge_features.json"

try:
    src_path = str(ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
except Exception:
    pass

from core.ticker_normalization import normalize_tickers

try:
    from core.sentry_runtime import install_global_excepthook, init_sentry, set_job_context, capture_exception
except Exception:  # pragma: no cover
    def install_global_excepthook(job_name: str) -> bool:
        return False

    def init_sentry(component: str) -> bool:
        return False

    def set_job_context(job_name: str, **context: Any) -> None:
        return None

    def capture_exception(exc: BaseException, *, job_name: str | None = None, context: Dict[str, Any] | None = None) -> None:
        return None


def _load_forecast_tickers() -> List[str]:
    try:
        obj = json.loads(FORECASTS_PATH.read_text())
        rows = obj.get("rows") or obj.get("data", {}).get("rows", []) or []
        tickers = normalize_tickers(
            (r.get("ticker") or r.get("symbol") or "") for r in rows if r.get("ticker") or r.get("symbol")
        )
        return sorted(tickers)
    except Exception as e:
        logger.warning(f"Cannot load forecasts.json: {e}")
        return []


def _compute_indicators(hist) -> Dict[str, Any]:
    if hist is None or hist.empty:
        return {}
    closes = hist["Close"].dropna()
    if closes.empty:
        return {}
    last_price = float(closes.iloc[-1])
    def momentum(series, window):
        if len(series) < window:
            return None
        return float(series.iloc[-1] / series.iloc[-window] - 1.0)
    def drawdown(series, window=60):
        if len(series) < window:
            return None
        window_series = series.iloc[-window:]
        peak = window_series.max()
        if peak == 0:
            return None
        trough = window_series.min()
        return float(trough / peak - 1.0)
    def sma(series, window):
        if len(series) < window:
            return None
        return float(series.iloc[-window:].mean())
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    pct = closes.pct_change()
    vol20 = float(pct.rolling(20).std().iloc[-1]) if len(pct) >= 20 else None
    mom_1m = momentum(closes, 21)
    mom_3m = momentum(closes, 63)
    dd_3m = drawdown(closes, 63)
    rsi = None
    if len(closes) > 14:
        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = (gain / (loss.replace(0, 1e-9))).iloc[-1]
        rsi = 100 - (100 / (1 + rs))
    out = {
        "last_price": last_price,
        "sma20_vs_price": round((sma20 - last_price) / last_price, 4) if sma20 else None,
        "sma50_vs_price": round((sma50 - last_price) / last_price, 4) if sma50 else None,
        "vol20": round(vol20, 4) if vol20 is not None else None,
        "rsi": round(rsi, 2) if rsi is not None else None,
        "momentum_1m": round(mom_1m, 4) if mom_1m is not None else None,
        "momentum_3m": round(mom_3m, 4) if mom_3m is not None else None,
        "drawdown_3m": round(dd_3m, 4) if dd_3m is not None else None,
    }
    if "Volume" in hist.columns and not hist["Volume"].dropna().empty:
        vol_avg20 = hist["Volume"].rolling(20).mean().iloc[-1]
        out["volume_avg20"] = int(vol_avg20) if vol_avg20 == vol_avg20 else None
        out["volume_last"] = int(hist["Volume"].iloc[-1])
    return out


def run():
    init_sentry("judge_enrich")
    try:
        import yfinance as yf
    except Exception as e:
        logger.error(f"yfinance not available: {e}")
        capture_exception(e, job_name="judge_enrich", context={"stage": "import_yfinance"})
        return {"ok": False, "error": "yfinance missing"}

    tickers = _load_forecast_tickers()
    set_job_context("judge_enrich", ticker_count=len(tickers))
    if not tickers:
        logger.warning("No tickers found in forecasts.json")
    features: Dict[str, Any] = {}
    for t in tickers:
        try:
            yt = yf.Ticker(t)
            hist = yt.history(period="6mo", interval="1d")
            tech = _compute_indicators(hist)
            info = yt.info if hasattr(yt, "info") else {}
            fundamentals = {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "marketCap": info.get("marketCap"),
                "beta": info.get("beta"),
                "pe": info.get("trailingPE") or info.get("forwardPE"),
                "avgVolume": info.get("averageVolume") or info.get("averageDailyVolume10Day") or info.get("averageVolume10days"),
                "eps": info.get("trailingEps") or info.get("forwardEps"),
                "dividendYield": info.get("dividendYield") or info.get("trailingAnnualDividendYield"),
                "nextEarningsDate": info.get("earningsTimestamp") or info.get("earningsTimestampStart") or info.get("earningsTimestampEnd"),
                # Margins & growth (si dispo)
                "profitMargins": info.get("profitMargins"),
                "operatingMargins": info.get("operatingMargins"),
                "grossMargins": info.get("grossMargins"),
                "revenueGrowth": info.get("revenueGrowth"),
                "ebitdaMargins": info.get("ebitdaMargins"),
                "bookValue": info.get("bookValue"),
                "priceToBook": info.get("priceToBook"),
            }
            features[t] = {
                "tech": tech,
                "fundamentals": fundamentals,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
            }
            logger.info(f"Enriched {t}: tech={tech} fundamentals={fundamentals}")
        except Exception as e:
            logger.warning(f"Failed to enrich {t}: {e}")
            capture_exception(
                e,
                job_name="judge_enrich",
                context={"stage": "enrich_ticker", "ticker": t},
            )

    payload = {"asof": datetime.utcnow().isoformat() + "Z", "tickers": features}
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    logger.info(f"Saved enriched judge features -> {OUTPUT_PATH}")
    if tickers and not features:
        capture_exception(
            RuntimeError("judge_enrich produced zero features"),
            job_name="judge_enrich",
            context={"ticker_count": len(tickers)},
        )
    return {"ok": True, "tickers": list(features.keys()), "path": str(OUTPUT_PATH)}


if __name__ == "__main__":
    install_global_excepthook("judge_enrich")
    out = run()
    print(out)
