"""
Heuristic execution-cost helpers shared by Judge surfaces.

These helpers stay dependency-light so backend tests can exercise the cost model
without importing the full Judge route module and its LLM/runtime stack.
"""

from typing import Any, Dict, Optional

_KNOWN_ETF_TICKERS = {
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "IVV",
    "VOO",
    "VTI",
    "EFA",
    "EEM",
    "TLT",
    "HYG",
    "LQD",
    "GLD",
    "SLV",
    "USO",
    "XLK",
    "XLF",
    "XLE",
    "XLI",
    "XLV",
    "XLP",
    "XLU",
    "VNQ",
}
_EXECUTION_COST_BANDS_BPS: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = {
    "equity": {
        "liquid": {
            "fees": {"low": 1.0, "base": 3.0, "high": 6.0},
            "slippage": {"low": 4.0, "base": 8.0, "high": 15.0},
        },
        "medium": {
            "fees": {"low": 2.0, "base": 4.0, "high": 8.0},
            "slippage": {"low": 10.0, "base": 18.0, "high": 32.0},
        },
        "illiquid": {
            "fees": {"low": 3.0, "base": 6.0, "high": 12.0},
            "slippage": {"low": 25.0, "base": 45.0, "high": 80.0},
        },
    },
    "etf": {
        "liquid": {
            "fees": {"low": 1.0, "base": 2.0, "high": 4.0},
            "slippage": {"low": 2.0, "base": 5.0, "high": 10.0},
        },
        "medium": {
            "fees": {"low": 1.0, "base": 3.0, "high": 6.0},
            "slippage": {"low": 5.0, "base": 10.0, "high": 18.0},
        },
        "illiquid": {
            "fees": {"low": 2.0, "base": 4.0, "high": 8.0},
            "slippage": {"low": 10.0, "base": 18.0, "high": 32.0},
        },
    },
    "crypto": {
        "liquid": {
            "fees": {"low": 8.0, "base": 12.0, "high": 18.0},
            "slippage": {"low": 10.0, "base": 18.0, "high": 30.0},
        },
        "medium": {
            "fees": {"low": 10.0, "base": 16.0, "high": 25.0},
            "slippage": {"low": 18.0, "base": 30.0, "high": 50.0},
        },
        "illiquid": {
            "fees": {"low": 12.0, "base": 20.0, "high": 35.0},
            "slippage": {"low": 30.0, "base": 50.0, "high": 90.0},
        },
    },
}
_TAX_RATE_BANDS: Dict[str, Dict[str, float]] = {
    "short_term": {"low": 0.0, "base": 0.20, "high": 0.37},
    "long_term": {"low": 0.0, "base": 0.10, "high": 0.20},
}


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _infer_execution_asset_class(
    *,
    ticker: str,
    row: Optional[Dict[str, Any]],
    features: Optional[Dict[str, Any]],
) -> str:
    feature_map = features if isinstance(features, dict) else {}
    fundamentals = (
        feature_map.get("fundamentals_enriched")
        if isinstance(feature_map.get("fundamentals_enriched"), dict)
        else feature_map.get("fundamentals")
    )
    if not isinstance(fundamentals, dict):
        fundamentals = {}

    if ticker.upper() in _KNOWN_ETF_TICKERS:
        return "etf"

    for candidate in (
        (row or {}).get("asset_class"),
        (row or {}).get("asset_type"),
        (row or {}).get("instrument_type"),
        (row or {}).get("quoteType"),
        feature_map.get("asset_class"),
        feature_map.get("asset_type"),
        feature_map.get("instrument_type"),
        feature_map.get("quoteType"),
        fundamentals.get("quoteType"),
        fundamentals.get("fundType"),
        fundamentals.get("instrumentType"),
        fundamentals.get("securityType"),
    ):
        text = str(candidate or "").strip().lower()
        if not text:
            continue
        if any(token in text for token in ("etf", "fund", "index")):
            return "etf"
        if any(token in text for token in ("crypto", "digital", "token", "coin")):
            return "crypto"

    return "equity"


def _infer_execution_liquidity_bucket(
    *,
    ticker: str,
    asset_class: str,
    features: Optional[Dict[str, Any]],
    price_features: Optional[Dict[str, Any]],
) -> str:
    feature_map = features if isinstance(features, dict) else {}
    fundamentals = (
        feature_map.get("fundamentals_enriched")
        if isinstance(feature_map.get("fundamentals_enriched"), dict)
        else feature_map.get("fundamentals")
    )
    if not isinstance(fundamentals, dict):
        fundamentals = {}

    avg_volume = _safe_float(
        feature_map.get("avgVolume")
        or fundamentals.get("avgVolume")
        or fundamentals.get("averageVolume")
    )
    market_cap = _safe_float(
        feature_map.get("marketCap")
        or fundamentals.get("marketCap")
        or fundamentals.get("market_cap")
    )
    realized_vol = _safe_float(
        ((price_features or {}).get("price_stats") or {}).get("vol_1m")
    )

    if asset_class == "etf" and ticker.upper() in _KNOWN_ETF_TICKERS:
        bucket = "liquid"
    elif asset_class == "crypto":
        if avg_volume is not None and avg_volume >= 100_000_000:
            bucket = "liquid"
        elif avg_volume is not None and avg_volume >= 25_000_000:
            bucket = "medium"
        else:
            bucket = "illiquid"
    else:
        if (
            (avg_volume is not None and avg_volume >= 5_000_000)
            or (market_cap is not None and market_cap >= 20_000_000_000)
        ):
            bucket = "liquid"
        elif (
            (avg_volume is not None and avg_volume >= 1_000_000)
            or (market_cap is not None and market_cap >= 2_000_000_000)
        ):
            bucket = "medium"
        else:
            bucket = "illiquid"

    if realized_vol is not None:
        if realized_vol >= 0.10:
            return "illiquid"
        if realized_vol >= 0.06 and bucket == "liquid":
            return "medium"
    return bucket


def _estimate_execution_costs(
    *,
    ticker: str,
    expected_return: Any,
    horizon: Optional[str],
    row: Optional[Dict[str, Any]],
    features: Optional[Dict[str, Any]],
    price_features: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    gross_return = _safe_float(expected_return)
    gross_bps = round(gross_return * 10_000.0, 2) if gross_return is not None else None
    asset_class = _infer_execution_asset_class(
        ticker=ticker,
        row=row,
        features=features,
    )
    liquidity_bucket = _infer_execution_liquidity_bucket(
        ticker=ticker,
        asset_class=asset_class,
        features=features,
        price_features=price_features,
    )
    direct_costs = (
        _EXECUTION_COST_BANDS_BPS.get(asset_class, {}).get(liquidity_bucket)
        or _EXECUTION_COST_BANDS_BPS["equity"]["medium"]
    )
    fees_bps = dict(direct_costs.get("fees") or {})
    slippage_bps = dict(direct_costs.get("slippage") or {})

    horizon_text = str(horizon or "").strip().lower()
    holding_period_bucket = (
        "long_term" if horizon_text in {"1y", "2y", "5y"} else "short_term"
    )
    tax_rates = dict(_TAX_RATE_BANDS[holding_period_bucket])

    tax_drag_bps: Dict[str, float] = {}
    total_cost_bps: Dict[str, float] = {}
    net_effect_bps: Dict[str, float] = {}
    for band in ("low", "base", "high"):
        tax_drag = round(max(gross_bps or 0.0, 0.0) * tax_rates[band], 2)
        total_cost = round(
            float(fees_bps.get(band, 0.0))
            + float(slippage_bps.get(band, 0.0))
            + tax_drag,
            2,
        )
        tax_drag_bps[band] = tax_drag
        total_cost_bps[band] = total_cost
        if gross_bps is not None:
            net_effect_bps[band] = round(gross_bps - total_cost, 2)

    net_return_base = (
        round(net_effect_bps["base"] / 10_000.0, 6)
        if "base" in net_effect_bps
        else None
    )

    # Low edge warning: trigger when net edge is thin after costs
    # Threshold: net <= 50 bps OR costs consume >= 40% of gross edge
    low_edge = bool(
        gross_bps is not None
        and gross_bps > 0
        and (
            net_effect_bps.get("base", 0.0) <= 50.0
            or net_effect_bps.get("base", 0.0) <= gross_bps * 0.60
        )
    )
    severity = "none"
    warning_message = None
    if low_edge:
        if net_effect_bps.get("base", 0.0) <= 0:
            severity = "high"
            warning_message = (
                f"Estimated net edge turns negative after default fees, slippage, "
                f"and tax drag for {asset_class}."
            )
        else:
            severity = "medium"
            warning_message = (
                f"Estimated net edge is thin after default fees, slippage, and tax "
                f"drag for {asset_class}."
            )

    return {
        "model_version": "judge_execution_costs_v1",
        "asset_class": asset_class,
        "liquidity_bucket": liquidity_bucket,
        "gross_expected_return": (
            round(gross_return, 6) if gross_return is not None else None
        ),
        "gross_expected_effect_bps": gross_bps,
        "net_expected_return": net_return_base,
        "net_expected_effect_bps": net_effect_bps or None,
        "costs_bps": {
            "fees": fees_bps,
            "slippage": slippage_bps,
            "tax_drag": tax_drag_bps,
            "total": total_cost_bps,
        },
        "tax_assumptions": {
            "holding_period_bucket": holding_period_bucket,
            "tax_rate_band": tax_rates,
            "applies_on_positive_return_only": True,
            "note": "Heuristic estimate for awareness only; not tax advice.",
        },
        "warning": {
            "low_edge": low_edge,
            "severity": severity,
            "message": warning_message,
        },
    }


def estimate_execution_costs(
    *,
    ticker: str,
    expected_return: Any,
    horizon: Optional[str],
    row: Optional[Dict[str, Any]],
    features: Optional[Dict[str, Any]],
    price_features: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Public wrapper for shared execution-cost estimation."""
    return _estimate_execution_costs(
        ticker=ticker,
        expected_return=expected_return,
        horizon=horizon,
        row=row,
        features=features,
        price_features=price_features,
    )
