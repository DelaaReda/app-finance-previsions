"""
Execution Costs API - Exposes tax, fee, and slippage awareness for decision-making.

This endpoint makes the existing cost model from judge_execution_costs.py
available to the frontend for gross vs net edge visualization.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

from storage.io import load_json
from core.ticker_normalization import normalize_ticker, normalize_tickers

try:
    from src.core.response import ok, err
except Exception:
    def ok(data):
        return {"ok": True, "data": data}

    def err(msg, code=500):
        return {"ok": False, "error": msg, "code": code}

try:
    from domains.judge.application.execution_costs import (
        _estimate_execution_costs,
        _infer_execution_asset_class,
        _infer_execution_liquidity_bucket,
    )
except ImportError:
    _estimate_execution_costs = None
    _infer_execution_asset_class = None
    _infer_execution_liquidity_bucket = None

try:
    from domains.judge.application.judge_endpoint_service import (
        REBALANCE_DEFAULT_FEE_BPS,
        REBALANCE_DEFAULT_SLIPPAGE_BPS,
        REBALANCE_SHORT_TERM_TAX_RATE,
        REBALANCE_LONG_TERM_TAX_RATE,
    )
except ImportError:
    REBALANCE_DEFAULT_FEE_BPS = 5.0
    REBALANCE_DEFAULT_SLIPPAGE_BPS = 10.0
    REBALANCE_SHORT_TERM_TAX_RATE = 0.30
    REBALANCE_LONG_TERM_TAX_RATE = 0.15

router = APIRouter()


@router.get("/api/execution-costs")
async def get_execution_costs(
    ticker: str = Query(..., description="Ticker symbol (e.g., SPY, NVDA, BTC)"),
    expected_return: Optional[float] = Query(None, description="Expected return (decimal, e.g., 0.05 for 5%)"),
    horizon: Optional[str] = Query(None, description="Investment horizon (1d, 1w, 1m, 3m, 1y)"),
    asset_class: Optional[str] = Query(None, description="Asset class override (equity, etf, crypto)"),
    debug: bool = Query(False, description="Enable debug mode with detailed breakdown"),
) -> Dict[str, Any]:
    """
    Get execution cost estimates for a ticker including fees, slippage, and tax drag.

    Returns gross vs net expected return after accounting for:
    - Trading fees (broker/commission)
    - Slippage (market impact)
    - Tax drag (short-term or long-term capital gains)

    Args:
        ticker: Ticker symbol
        expected_return: Optional expected return (uses model estimate if not provided)
        horizon: Investment horizon for tax bucket determination
        asset_class: Optional asset class override
        debug: If true, includes detailed breakdown and disables cache

    Returns:
        Cost breakdown with gross/net returns and warnings for low-edge situations
    """
    try:
        ticker = normalize_ticker(ticker)
        if not ticker:
            raise HTTPException(status_code=400, detail="Invalid ticker symbol")

        # Use existing cost model if available
        if _estimate_execution_costs is not None:
            # Build minimal row/features for cost estimation
            row: Dict[str, Any] = {}
            if asset_class:
                row["asset_class"] = asset_class

            features: Dict[str, Any] = {}
            if asset_class:
                features["asset_class"] = asset_class

            # Get cost estimate from existing model
            cost_estimate = _estimate_execution_costs(
                ticker=ticker,
                expected_return=expected_return if expected_return is not None else 0.05,
                horizon=horizon,
                row=row if row else None,
                features=features if features else None,
                price_features=None,
            )
        else:
            # Fallback simple cost model
            cost_estimate = _simple_cost_estimate(
                ticker=ticker,
                expected_return=expected_return,
                horizon=horizon,
                asset_class=asset_class,
            )

        # Add metadata
        result = {
            "ticker": ticker,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": ["judge_execution_costs_v1"],
            "model_version": "execution_costs_v1",
            "cost_estimate": cost_estimate,
            "defaults": {
                "fee_bps": REBALANCE_DEFAULT_FEE_BPS,
                "slippage_bps": REBALANCE_DEFAULT_SLIPPAGE_BPS,
                "short_term_tax_rate": REBALANCE_SHORT_TERM_TAX_RATE,
                "long_term_tax_rate": REBALANCE_LONG_TERM_TAX_RATE,
            },
        }

        # Add debug info if requested
        if debug:
            result["debug"] = {
                "input_params": {
                    "ticker": ticker,
                    "expected_return": expected_return,
                    "horizon": horizon,
                    "asset_class": asset_class,
                },
                "inference_steps": [
                    "1. Infer asset class from ticker/features",
                    "2. Infer liquidity bucket from volume/market cap",
                    "3. Look up cost bands for asset class + liquidity",
                    "4. Calculate tax drag based on horizon",
                    "5. Compute net effect = gross - (fees + slippage + tax)",
                ],
            }

        return ok(result)

    except HTTPException:
        raise
    except Exception as e:
        if debug:
            import traceback
            return err({"message": str(e), "traceback": traceback.format_exc()}, code=500)
        return err(str(e), code=500)


def _simple_cost_estimate(
    ticker: str,
    expected_return: Optional[float],
    horizon: Optional[str],
    asset_class: Optional[str],
) -> Dict[str, Any]:
    """Simple fallback cost estimation when full model is unavailable."""
    # Determine asset class
    if asset_class:
        ac = asset_class.lower()
    elif ticker.upper() in {"SPY", "QQQ", "IWM", "DIA", "GLD", "SLV", "TLT"}:
        ac = "etf"
    elif any(x in ticker.upper() for x in {"BTC", "ETH"}):
        ac = "crypto"
    else:
        ac = "equity"

    # Simple cost bands (bps)
    cost_bands = {
        "equity": {"fees": 3.0, "slippage": 8.0},
        "etf": {"fees": 2.0, "slippage": 5.0},
        "crypto": {"fees": 12.0, "slippage": 18.0},
    }

    costs = cost_bands.get(ac, cost_bands["equity"])

    # Determine tax bucket
    horizon_text = str(horizon or "").lower()
    tax_bucket = "long_term" if horizon_text in {"1y", "2y", "5y"} else "short_term"
    tax_rate = REBALANCE_LONG_TERM_TAX_RATE if tax_bucket == "long_term" else REBALANCE_SHORT_TERM_TAX_RATE

    # Calculate costs
    gross_return = expected_return if expected_return is not None else 0.05
    gross_bps = gross_return * 10_000
    total_cost_bps = costs["fees"] + costs["slippage"]

    # Tax drag only on positive returns
    tax_drag_bps = max(0.0, gross_bps) * tax_rate if gross_bps > 0 else 0.0
    total_with_tax_bps = total_cost_bps + tax_drag_bps
    net_bps = gross_bps - total_with_tax_bps
    net_return = net_bps / 10_000

    # Low edge warning
    low_edge = gross_bps > 0 and (net_bps <= 25.0 or net_bps <= gross_bps * 0.25)
    severity = "none"
    warning_message = None
    if low_edge:
        if net_bps <= 0:
            severity = "high"
            warning_message = "Estimated net edge turns negative after costs and tax drag."
        else:
            severity = "medium"
            warning_message = "Estimated net edge is thin after costs and tax drag."

    return {
        "model_version": "simple_costs_v1",
        "asset_class": ac,
        "liquidity_bucket": "base",
        "gross_expected_return": gross_return,
        "gross_expected_effect_bps": round(gross_bps, 2),
        "net_expected_return": round(net_return, 6),
        "net_expected_effect_bps": round(net_bps, 2),
        "costs_bps": {
            "fees": costs["fees"],
            "slippage": costs["slippage"],
            "tax_drag": round(tax_drag_bps, 2),
            "total": round(total_with_tax_bps, 2),
        },
        "tax_assumptions": {
            "holding_period_bucket": tax_bucket,
            "tax_rate": tax_rate,
            "applies_on_positive_return_only": True,
            "note": "Simple heuristic estimate; not tax advice.",
        },
        "warning": {
            "low_edge": low_edge,
            "severity": severity,
            "message": warning_message,
        },
    }


@router.get("/api/execution-costs/universe")
async def get_execution_costs_universe(
    tickers: str = Query(..., description="Comma-separated tickers (e.g., SPY,QQQ,GLD)"),
    expected_return: Optional[float] = Query(None, description="Default expected return for all tickers"),
    horizon: Optional[str] = Query(None, description="Default horizon for all tickers"),
) -> Dict[str, Any]:
    """Get execution cost estimates for multiple tickers at once."""
    try:
        # Split comma-separated tickers manually since normalize_tickers expects a list
        ticker_list = [normalize_ticker(t.strip()) for t in tickers.split(",") if t.strip()]
        ticker_list = [t for t in ticker_list if t]  # Remove empty/invalid
        if not ticker_list:
            raise HTTPException(status_code=400, detail="No valid tickers provided")

        results = {}
        for t in ticker_list:
            # Call individual endpoint logic
            single_result = await get_execution_costs(
                ticker=t,
                expected_return=expected_return,
                horizon=horizon,
                debug=False,
            )
            if single_result.get("ok"):
                results[t] = single_result["data"]["cost_estimate"]
            else:
                results[t] = {"error": single_result.get("error", "Unknown error")}

        return ok({
            "tickers": ticker_list,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cost_estimates": results,
        })

    except HTTPException:
        raise
    except Exception as e:
        return err(str(e), code=500)
