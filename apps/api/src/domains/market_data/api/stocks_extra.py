"""
Stocks Extra API Routes - Finance Copilot System
Additional endpoints for advanced stock analysis features.
Task: FC-API-027 - Stock Correlation Heatmap.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Query

from core.response import ok

router = APIRouter()
logger = logging.getLogger(__name__)

try:
    from src.services.correlation_service import get_correlation_matrix as load_correlation_matrix
except ImportError:  # pragma: no cover
    try:
        from services.correlation_service import get_correlation_matrix as load_correlation_matrix  # type: ignore
    except ImportError:  # pragma: no cover
        try:
            from backend.services.correlation_service import get_correlation_matrix as load_correlation_matrix  # type: ignore
        except ImportError:  # pragma: no cover
            load_correlation_matrix = None


def _normalize_ticker_list(raw_tickers: Optional[List[str]]) -> List[str]:
    normalized: List[str] = []
    seen = set()
    for raw in raw_tickers or []:
        for token in str(raw).replace(" ", "").split(","):
            token = token.strip().upper()
            if token and token not in seen:
                normalized.append(token)
                seen.add(token)
    return normalized


def _extract_matrix_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"matrix": {}, "tickers": [], "lookback_days": 0}

    matrix = payload.get("matrix")
    if isinstance(matrix, dict):
        tickers = payload.get("tickers", [])
        if not isinstance(tickers, list):
            tickers = list(matrix.keys())
        return {
            "matrix": matrix,
            "tickers": tickers,
            "lookback_days": payload.get("lookback_days"),
            "generated_at": payload.get("generated_at"),
            "source": payload.get("source"),
        }

    # Fallback for legacy list-of-lists structure.
    rows = payload.get("rows") or payload.get("columns") or []
    if isinstance(rows, list) and rows and isinstance(matrix, list):
        row_tickers = rows
        matrix_lookup: Dict[str, Dict[str, float]] = {}
        for row_index, row_name in enumerate(row_tickers):
            row_key = str(row_name).upper()
            row_values = matrix[row_index] if row_index < len(matrix) else []
            matrix_row = {}
            for col_index, col_name in enumerate(row_tickers):
                col_key = str(col_name).upper()
                if col_index < len(row_values):
                    value = row_values[col_index]
                    if isinstance(value, (int, float)):
                        matrix_row[col_key] = float(value)
            matrix_lookup[row_key] = matrix_row
        return {
            "matrix": matrix_lookup,
            "tickers": row_tickers,
            "lookback_days": payload.get("lookback_days"),
            "generated_at": payload.get("generated_at"),
            "source": payload.get("source"),
        }

    return {"matrix": {}, "tickers": [], "lookback_days": 0}


def _build_matrix_table(matrix: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    table: List[Dict[str, Any]] = []
    for ticker in sorted(matrix.keys()):
        row = matrix[ticker]
        row_payload = {"ticker": ticker}
        for col in sorted(matrix.keys()):
            row_payload[col] = float(row.get(col, 0.0))
        table.append(row_payload)
    return table


def _filter_matrix(
    matrix: Dict[str, Dict[str, float]],
    selected_tickers: List[str],
    min_correlation: float,
    max_correlation: float,
    limit: int,
) -> Dict[str, Dict[str, float]]:
    tickers = [ticker for ticker in sorted(matrix.keys()) if not selected_tickers or ticker in selected_tickers]
    if limit and len(tickers) > limit:
        tickers = tickers[:limit]

    filtered: Dict[str, Dict[str, float]] = {}
    for row_ticker in tickers:
        row = matrix.get(row_ticker, {})
        filtered_row: Dict[str, float] = {}
        for col_ticker in tickers:
            value = row.get(col_ticker)
            if value is None or not isinstance(value, (int, float)):
                continue
            if min_correlation <= value <= max_correlation:
                filtered_row[col_ticker] = float(value)
        if filtered_row:
            filtered[row_ticker] = filtered_row
    return filtered


@router.get("/stocks/heatmap")
def get_stock_correlation_heatmap(
    tickers: Optional[List[str]] = Query(None, description="Filter by specific tickers (comma-separated)"),
    window: Optional[str] = Query("30d", description="Time window: 7d, 30d, 90d, 1y"),
    method: Optional[str] = Query("pearson", description="Correlation method: pearson, spearman, kendall"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Limit number of results (max 200)"),
    min_correlation: Optional[float] = Query(-1.0, description="Minimum correlation threshold (-1.0 to 1.0)"),
    max_correlation: Optional[float] = Query(1.0, description="Maximum correlation threshold (-1.0 to 1.0)"),
) -> Dict[str, Any]:
    """
    Return a correlation matrix for selected tickers.
    """
    try:
        requested_tickers = _normalize_ticker_list(tickers)
        limit_count = int(limit or 50)
        min_value = float(min_correlation if min_correlation is not None else -1.0)
        max_value = float(max_correlation if max_correlation is not None else 1.0)

        logger.info(
            "Correlation heatmap requested",
            extra={
                "tickers": requested_tickers,
                "window": window,
                "method": method,
                "limit": limit_count,
            },
        )

        source_matrix = {}
        if load_correlation_matrix:
            source_matrix = _extract_matrix_payload(load_correlation_matrix())
        matrix = source_matrix.get("matrix", {}) if isinstance(source_matrix, dict) else {}

        if not matrix:
            return ok({
                "matrix": {},
                "matrix_table": [],
                "tickers": requested_tickers,
                "rows": requested_tickers,
                "columns": requested_tickers,
                "method": method,
                "start_date": datetime.utcnow().isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "generated_at": datetime.utcnow().isoformat(),
                "message": "No cached correlation matrix available for this request.",
                "freshness": "unknown",
                "source": ["fallback_empty", "correlation_heatmap"],
                "filters": {
                    "tickers": requested_tickers,
                    "window": window,
                    "method": method,
                    "limit": limit_count,
                    "min_correlation": min_value,
                    "max_correlation": max_value,
                },
                "metadata": {
                    "symbols_count": len(requested_tickers),
                    "data_points_per_symbol": 0,
                    "computation_method": method,
                    "correlation_range": {"min": 0.0, "max": 0.0, "avg": 0.0},
                    "valid_pairs": 0,
                },
            })

        filtered_matrix = _filter_matrix(
            matrix=matrix,
            selected_tickers=requested_tickers,
            min_correlation=min_value,
            max_correlation=max_value,
            limit=limit_count,
        )
        rows = sorted(filtered_matrix.keys())
        correlation_values = []
        for row in rows:
            for col, value in filtered_matrix.get(row, {}).items():
                if row == col:
                    continue
                correlation_values.append(float(value))

        if correlation_values:
            min_corr = min(correlation_values)
            max_corr = max(correlation_values)
            avg_corr = sum(correlation_values) / len(correlation_values)
        else:
            min_corr = 0.0
            max_corr = 0.0
            avg_corr = 0.0

        payload = {
            "matrix": filtered_matrix,
            "matrix_table": _build_matrix_table(filtered_matrix),
            "tickers": rows,
            "rows": rows,
            "columns": rows,
            "method": method,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "generated_at": source_matrix.get("generated_at") or datetime.utcnow().isoformat(),
            "freshness": source_matrix.get("freshness", "cached"),
            "source": source_matrix.get("source", ["correlation_matrix", "correlation_service"]),
            "lookback_days": source_matrix.get("lookback_days", 90),
            "filters": {
                "tickers": requested_tickers,
                "window": window,
                "method": method,
                "limit": limit_count,
                "min_correlation": min_value,
                "max_correlation": max_value,
            },
            "metadata": {
                "symbols_count": len(rows),
                "data_points_per_symbol": 0,
                "computation_method": method,
                "correlation_range": {
                    "min": float(min_corr),
                    "max": float(max_corr),
                    "avg": float(avg_corr),
                },
                "valid_pairs": len(correlation_values),
            },
        }
        logger.info("Correlation heatmap generated for %s tickers using %s", len(rows), method)
        return ok(payload)

    except Exception as e:
        logger.error("Error in correlation heatmap endpoint: %s", str(e), exc_info=True)
        return ok({
            "matrix": {},
            "matrix_table": [],
            "tickers": [],
            "rows": [],
            "columns": [],
            "method": method,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Correlation heatmap temporarily unavailable - showing fallback data",
            "freshness": "error",
            "source": ["correlation_heatmap", "error_fallback"],
            "filters": {
                "tickers": requested_tickers if "requested_tickers" in locals() else [],
                "window": window,
                "method": method,
                "limit": limit,
            },
            "metadata": {
                "symbols_count": 0,
                "data_points_per_symbol": 0,
                "computation_method": method,
                "correlation_range": {"min": 0.0, "max": 0.0, "avg": 0.0},
                "valid_pairs": 0,
            },
        })


@router.get("/stocks/correlations")
def get_stock_correlations(
    base_ticker: str = Query(..., description="Base ticker to measure correlations against"),
    compare_tickers: Optional[List[str]] = Query(None, description="Tickers to compare against base (comma-separated)"),
    window: Optional[str] = Query("30d", description="Time window for correlation calculation"),
    method: Optional[str] = Query("pearson", description="Correlation method: pearson, spearman, kendall"),
) -> Dict[str, Any]:
    """
    Return correlations of a base ticker versus a provided ticker list.
    """
    try:
        base = str(base_ticker).strip().upper()
        compare = _normalize_ticker_list(compare_tickers)
        logger.info("Getting correlations for %s vs %s", base, compare)

        heatmap = get_stock_correlation_heatmap(
            tickers=[base] + compare,
            window=window,
            method=method,
            limit=50,
            min_correlation=-1.0,
            max_correlation=1.0,
        )
        if not heatmap.get("ok"):
            return heatmap

        data = heatmap.get("data", {})
        matrix = data.get("matrix", {})
        base_row = matrix.get(base, {})
        base_correlations = {
            ticker: value
            for ticker, value in base_row.items()
            if ticker != base and isinstance(value, (int, float))
        }

        if compare:
            compare_set = set(compare)
            base_correlations = {
                ticker: base_correlations[ticker]
                for ticker in list(base_correlations.keys())
                if ticker in compare_set
            }

        data["base_ticker"] = base
        data["base_correlations"] = base_correlations
        data["method"] = method
        heatmap["data"] = data
        return heatmap

    except Exception as e:
        logger.error("Error in stock correlations endpoint: %s", str(e), exc_info=True)
        return ok({
            "base_ticker": base_ticker,
            "correlations": {},
            "compare_tickers": compare_tickers,
            "method": method,
            "window": window,
            "generated_at": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Stock correlations temporarily unavailable - showing fallback data",
            "source": ["stock_correlations", "error_fallback"],
        })

# Export the router for the main application to include
stocks_extra_router = router
