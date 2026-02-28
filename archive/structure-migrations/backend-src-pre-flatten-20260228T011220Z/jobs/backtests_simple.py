"""
Simple backtests job
Computes a lightweight hit rate and average return across latest daily moves
and persists a minimal snapshot to data/backtests.json.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

from storage.io import save_json, load_json
from src.core.market_data import get_price_history  # type: ignore


def run_backtests_simple() -> Dict[str, Any]:
    try:
        forecasts = load_json("forecasts") or {}
        rows: List[Dict[str, Any]] = (
            forecasts.get("rows")
            or forecasts.get("data", {}).get("rows", [])
            or []
        )
        # Build unique latest direction per ticker
        latest: Dict[str, str] = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            t = str(r.get("ticker") or r.get("symbol") or "").upper()
            if not t:
                continue
            d = str(r.get("direction") or "").lower()
            latest[t] = d

        import requests as _rq
        from urllib.parse import urlencode

        hits = total = 0
        all_rets: List[float] = []
        for t, pred in list(latest.items())[:50]:
            try:
                df = get_price_history(t, interval="1d")
                r1 = r0 = None
                if df is not None and hasattr(df, "empty") and not df.empty and "Close" in df.columns:
                    close = df["Close"].dropna()
                    if len(close) >= 2:
                        r1 = float(close.iloc[-1])
                        r0 = float(close.iloc[-2])
                if r0 is None or r1 is None:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?" + urlencode({"range":"2d","interval":"1d"})
                    js = _rq.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"}).json()
                    result = (js.get('chart',{}).get('result') or [None])[0]
                    closes = (result.get('indicators',{}).get('quote') or [{}])[0].get('close', []) if result else []
                    if isinstance(closes, list) and len(closes) >= 2 and closes[-1] is not None and closes[-2] is not None:
                        r1 = float(closes[-1]); r0 = float(closes[-2])
                if r0 is None or r1 is None or r0 == 0:
                    continue
                ret = (r1 - r0) / r0
                all_rets.append(ret)
                if pred in ("up", "down"):
                    total += 1
                    if (pred == "up" and ret > 0) or (pred == "down" and ret < 0):
                        hits += 1
            except Exception:
                continue

        hit_rate = (hits / total) if total > 0 else 0.0
        avg_ret = (sum(all_rets) / len(all_rets)) if all_rets else 0.0
        now = datetime.utcnow().isoformat() + "Z"
        payload = {
            "results": {
                "ok": True,
                "total_trades": total,
                "hits": hits,
                "hit_rate": hit_rate,
                "avg_return": avg_ret,
                "timestamp": now,
            },
            "overall_metrics": {
                "hit_rate": hit_rate,
                "avg_return": avg_ret,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "n_trades": total,
                "total_trades": total,
            },
            "generated_at": now,
            "source": ["backtests_simple"],
        }
        save_json("backtests", payload, source=["job:backtests_simple"])  # type: ignore
        return payload
    except Exception as e:
        now = datetime.utcnow().isoformat() + "Z"
        fallback = {
            "results": {"ok": False, "error": str(e), "timestamp": now},
            "overall_metrics": {
                "hit_rate": 0.0,
                "avg_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "n_trades": 0,
                "total_trades": 0,
            },
            "generated_at": now,
            "source": ["backtests_simple", "error"],
        }
        try:
            save_json("backtests", fallback, source=["job:backtests_simple", "error"])  # type: ignore
        except Exception:
            pass
        return fallback


if __name__ == "__main__":
    out = run_backtests_simple()
    print(out)

