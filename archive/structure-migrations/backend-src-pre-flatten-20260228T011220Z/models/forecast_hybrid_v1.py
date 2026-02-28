"""
ForecastHybridV1 - lightweight forecast generator.

Uses cached prices from data/stocks/prices.json when available (offline-friendly),
and falls back to analytics.forecaster if needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from storage.io import load_json


def _parse_ts(ts_val: Any) -> Optional[datetime]:
    if ts_val is None:
        return None
    if isinstance(ts_val, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(ts_val), tz=timezone.utc)
            return dt
        except Exception:
            return None
    s = str(ts_val).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _sign(x: float) -> int:
    if x > 1e-12:
        return 1
    if x < -1e-12:
        return -1
    return 0


def _direction_from_return(ret: float) -> str:
    if ret > 0.001:
        return "up"
    if ret < -0.001:
        return "down"
    return "flat"


def _load_cached_prices() -> Dict[str, List[Tuple[datetime, float]]]:
    payload = load_json("stocks/prices") or {}
    tickers_block = payload.get("tickers") if isinstance(payload, dict) else {}
    out: Dict[str, List[Tuple[datetime, float]]] = {}
    if not isinstance(tickers_block, dict):
        return out
    for ticker, block in tickers_block.items():
        if not isinstance(block, dict):
            continue
        points = block.get("points")
        if not isinstance(points, list):
            continue
        parsed: List[Tuple[datetime, float]] = []
        for point in points:
            if not isinstance(point, list) or len(point) < 2:
                continue
            ts = _parse_ts(point[0])
            if ts is None:
                continue
            try:
                px = float(point[1])
            except Exception:
                continue
            if px <= 0:
                continue
            parsed.append((ts, px))
        if parsed:
            parsed.sort(key=lambda x: x[0])
            out[str(ticker).upper()] = parsed
    return out


def _load_judge_features() -> Dict[str, Dict[str, Any]]:
    payload = load_json("judge_features") or {}
    tickers = payload.get("tickers") if isinstance(payload, dict) else {}
    if not isinstance(tickers, dict):
        return {}
    return {str(k).upper(): v for k, v in tickers.items() if isinstance(v, dict)}


def _momentum_metrics(points: List[Tuple[datetime, float]]) -> Dict[str, Any]:
    if len(points) < 6:
        return {}
    prices = [p[1] for p in points]
    last = prices[-1]
    ret_5 = (last / prices[-6]) - 1.0 if len(prices) >= 6 else 0.0
    ret_20 = (last / prices[-21]) - 1.0 if len(prices) >= 21 else ret_5
    ret_60 = (last / prices[-61]) - 1.0 if len(prices) >= 61 else ret_20
    return {
        "ret_5": float(ret_5),
        "ret_20": float(ret_20),
        "ret_60": float(ret_60),
    }


def _confidence_from_momentum(ret_5: float, ret_20: float, price_age_days: float) -> float:
    mag = min(0.25, abs(ret_5))
    conf = 0.45 + (mag / 0.25) * 0.35
    if _sign(ret_5) != 0 and _sign(ret_5) == _sign(ret_20):
        conf += 0.05
    if price_age_days > 5:
        conf -= min(0.2, (price_age_days / 30.0) * 0.2)
    return _clamp(conf, 0.15, 0.85)


@dataclass
class ForecastRow:
    ticker: str
    direction: str
    confidence: float
    expected_return: float
    horizon: str
    timestamp: str
    asset_type: str
    source: List[str]
    model_version: str
    score: float
    probability: float
    explanation: str
    risk_factors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "direction": self.direction,
            "confidence": round(float(self.confidence), 4),
            "expected_return": round(float(self.expected_return), 4),
            "horizon": self.horizon,
            "timestamp": self.timestamp,
            "asset_type": self.asset_type,
            "source": self.source,
            "model_version": self.model_version,
            "score": round(float(self.score), 6),
            "probability": round(float(self.probability), 4),
            "explanation": self.explanation,
            "risk_factors": self.risk_factors,
        }


class ForecastHybridV1:
    """
    Hybrid forecast engine.
    Prefers cached prices (offline-friendly) then falls back to analytics.forecaster.
    """

    def __init__(self) -> None:
        self.model_version = "hybrid_v1_local_momentum"
        self.source = ["forecast_hybrid_v1", "local_momentum"]

    def run_forecast_job(self, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        tickers = tickers or [
            "SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "META"
        ]
        now = datetime.now(timezone.utc)
        ts = now.isoformat().replace("+00:00", "Z")

        cached = _load_cached_prices()
        judge_features = _load_judge_features()
        rows: List[Dict[str, Any]] = []

        for t in tickers:
            ticker = str(t).upper()
            points = cached.get(ticker) or []
            if points:
                metrics = _momentum_metrics(points)
                if not metrics:
                    rows.append(self._fallback_row(ticker, ts, reason="insufficient_points"))
                    continue
                ret_5 = float(metrics.get("ret_5", 0.0))
                ret_20 = float(metrics.get("ret_20", ret_5))
                last_ts = points[-1][0]
                price_age_days = max(0.0, (now - last_ts).total_seconds() / 86400.0)

                direction = _direction_from_return(ret_5)
                confidence = _confidence_from_momentum(ret_5, ret_20, price_age_days)
                expected_return = ret_5
                score = confidence * abs(expected_return)
                explanation = (
                    f"Momentum 5d={ret_5:+.2%}, 20d={ret_20:+.2%}; "
                    f"price_age={price_age_days:.1f}d."
                )
                risk_factors = []
                if price_age_days > 7:
                    risk_factors.append("price_data_stale")

                row = ForecastRow(
                    ticker=ticker,
                    direction=direction,
                    confidence=confidence,
                    expected_return=expected_return,
                    horizon="1w",
                    timestamp=ts,
                    asset_type="equity",
                    source=self.source,
                    model_version=self.model_version,
                    score=score,
                    probability=confidence,
                    explanation=explanation,
                    risk_factors=risk_factors,
                )
                rows.append(row.to_dict())
                continue

            # fallback to judge_features momentum if available
            jf = judge_features.get(ticker) or {}
            tech = jf.get("tech") if isinstance(jf, dict) else {}
            if isinstance(tech, dict):
                mom_1m = tech.get("momentum_1m")
                mom_3m = tech.get("momentum_3m")
                try:
                    exp_ret = float(mom_1m) / 4.0 if mom_1m is not None else (
                        float(mom_3m) / 12.0 if mom_3m is not None else 0.0
                    )
                except Exception:
                    exp_ret = 0.0
                direction = _direction_from_return(exp_ret)
                confidence = _clamp(0.35 + min(0.25, abs(exp_ret)) * 2.0, 0.2, 0.75)
                score = confidence * abs(exp_ret)
                explanation = "Fallback to judge_features momentum."
                rows.append(
                    ForecastRow(
                        ticker=ticker,
                        direction=direction,
                        confidence=confidence,
                        expected_return=exp_ret,
                        horizon="1w",
                        timestamp=ts,
                        asset_type="equity",
                        source=["forecast_hybrid_v1", "judge_features_fallback"],
                        model_version="hybrid_v1_jf_fallback",
                        score=score,
                        probability=confidence,
                        explanation=explanation,
                        risk_factors=["missing_prices_cache"],
                    ).to_dict()
                )
                continue

            # fallback to forecaster if cache missing
            rows.append(self._fallback_row(ticker, ts, reason="no_cached_prices"))

        return {
            "rows": rows,
            "last_update": ts,
            "model_version": self.model_version,
            "source": self.source,
        }

    def _fallback_row(self, ticker: str, ts: str, reason: str) -> Dict[str, Any]:
        try:
            from analytics.forecaster import forecast_ticker
            fr = forecast_ticker(ticker, horizon="1w")
            expected_return = fr.expected_return or 0.0
            confidence = _clamp(float(fr.confidence), 0.15, 0.85)
            score = confidence * abs(expected_return)
            explanation = f"Forecast fallback ({reason}) via SMA baseline."
            return ForecastRow(
                ticker=ticker,
                direction=fr.direction,
                confidence=confidence,
                expected_return=expected_return,
                horizon=fr.horizon,
                timestamp=ts,
                asset_type="equity",
                source=["forecast_hybrid_v1", "sma_fallback"],
                model_version="hybrid_v1_sma_fallback",
                score=score,
                probability=confidence,
                explanation=explanation,
                risk_factors=[reason],
            ).to_dict()
        except Exception:
            return ForecastRow(
                ticker=ticker,
                direction="flat",
                confidence=0.2,
                expected_return=0.0,
                horizon="1w",
                timestamp=ts,
                asset_type="equity",
                source=["forecast_hybrid_v1", "hard_fallback"],
                model_version="hybrid_v1_fallback",
                score=0.0,
                probability=0.2,
                explanation=f"Fallback: {reason}.",
                risk_factors=[reason],
            ).to_dict()
