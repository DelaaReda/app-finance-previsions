"""
Backtests job v2 (2026-03-03)
Hit-rate from local API only — no Yahoo Finance, no timeout.
"""
from __future__ import annotations

import urllib.request
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

from storage.io import save_json, load_json


def _coerce_ts(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    return None


def _fetch_local(path, timeout=4):
    try:
        with urllib.request.urlopen(f"http://localhost:8050{path}", timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def _get_price_change(ticker):
    """Get 1d change% from local API. Returns None if unavailable."""
    data = _fetch_local(f"/api/stocks/{ticker}")
    if data:
        inner = data.get("data", data)
        pct = inner.get("price_change_pct") or inner.get("change_percent")
        if pct is not None:
            try:
                v = float(pct)
                if v != 0.0:
                    return v
            except Exception:
                pass

    data2 = _fetch_local(f"/api/stocks/prices?ticker={ticker}&timeframe=2d&downsample=5")
    if data2:
        inner = data2.get("data", data2)
        points = inner.get("points", [])
        if isinstance(points, list) and len(points) >= 2:
            norm = []
            for p in points:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    norm.append((float(p[0] or 0), float(p[1] or 0)))
                elif isinstance(p, dict):
                    v = float(p.get("price") or p.get("close") or 0)
                    norm.append((float(p.get("ts", 0)), v))
            norm = sorted((ts, v) for ts, v in norm if v > 0)
            if len(norm) >= 2:
                prev, curr = norm[-2][1], norm[-1][1]
                if prev > 0:
                    return round((curr - prev) / prev * 100, 3)
    return None


def _build_payload(hits, total, all_rets, status):
    hit_rate = hits / total if total > 0 else 0.0
    avg_ret = sum(all_rets) / len(all_rets) if all_rets else 0.0
    sharpe = 0.0
    if len(all_rets) >= 3:
        mean = avg_ret
        variance = sum((r - mean) ** 2 for r in all_rets) / len(all_rets)
        std = math.sqrt(variance)
        if std > 0:
            sharpe = round((mean / std) * (252 ** 0.5), 2)
    now_iso = datetime.utcnow().isoformat() + "Z"
    return {
        "results": {
            "ok": status == "ok",
            "total_trades": total,
            "hits": hits,
            "hit_rate": round(hit_rate, 4),
            "avg_return": round(avg_ret, 6),
            "status": status,
            "timestamp": now_iso,
        },
        "overall_metrics": {
            "hit_rate": round(hit_rate, 4),
            "avg_return": round(avg_ret, 6),
            "sharpe_ratio": sharpe,
            "max_drawdown": 0.0,
            "n_trades": total,
            "total_trades": total,
        },
        "generated_at": now_iso,
        "source": ["backtests_simple_v2"],
    }


def run_backtests_simple():
    try:
        forecasts = load_json("forecasts") or {}
        rows = (
            forecasts.get("rows")
            or forecasts.get("data", {}).get("rows", [])
            or []
        )

        now = datetime.now(timezone.utc)
        min_ts = now - timedelta(days=7)
        latest = {}

        for r in rows:
            if not isinstance(r, dict):
                continue
            ticker = str(r.get("ticker") or r.get("symbol") or "").upper().strip()
            if not ticker:
                continue
            direction = str(r.get("direction") or "").lower()
            if direction not in ("up", "down"):
                continue
            ts = _coerce_ts(
                r.get("generated_at") or r.get("last_update")
                or r.get("freshness") or r.get("saved_at")
            )
            if ts is None or ts < min_ts:
                continue
            prev = latest.get(ticker)
            if prev is None or ts > prev[1]:
                latest[ticker] = (direction, ts)

        predictions = {t: d for t, (d, _) in latest.items()}

        if not predictions:
            payload = _build_payload(0, 0, [], "pending_no_forecasts")
            save_json("backtests", payload, source=["job:backtests_simple"])
            return payload

        hits = total = 0
        all_rets = []

        for ticker, pred in list(predictions.items())[:40]:
            change_pct = _get_price_change(ticker)
            if change_pct is None:
                continue
            ret = change_pct / 100.0
            all_rets.append(ret)
            total += 1
            if (pred == "up" and ret > 0) or (pred == "down" and ret < 0):
                hits += 1

        payload = _build_payload(hits, total, all_rets, "ok")
        save_json("backtests", payload, source=["job:backtests_simple"])
        return payload

    except Exception as e:
        now_iso = datetime.utcnow().isoformat() + "Z"
        fallback = {
            "results": {"ok": False, "error": str(e), "timestamp": now_iso},
            "overall_metrics": {
                "hit_rate": 0.0, "avg_return": 0.0,
                "sharpe_ratio": 0.0, "max_drawdown": 0.0,
                "n_trades": 0, "total_trades": 0,
            },
            "generated_at": now_iso,
            "source": ["backtests_simple", "error"],
        }
        try:
            save_json("backtests", fallback, source=["job:backtests_simple", "error"])
        except Exception:
            pass
        return fallback


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    out = run_backtests_simple()
    m = out.get("overall_metrics", {})
    print(f"hit_rate={m.get('hit_rate')} n_trades={m.get('n_trades')} sharpe={m.get('sharpe_ratio')}")
