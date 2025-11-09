"""
Prediction Analytics API Routes
Task: FC-API-031 - Prediction Accuracy Analytics
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from services.prediction_analyzer import prediction_analyzer_service
from storage.io import load_json
from services.cache_layer import load_or_compute

router = APIRouter(prefix="/api", tags=["analytics"])

@router.get("/analytics/predictions")
async def analytics_predictions(
    ticker: List[str] = Query(None, description="Filtrer par ticker (ex: NVDA,AAPL,MSFT)"),
    horizon: Optional[str] = Query(None, description="Filtrer par horizon (1d, 1w, 1m, 3m)"),
    days_back: int = Query(30, ge=1, le=365, description="Nombre de jours d'historique à analyser"),
    model_version: Optional[str] = Query(None, description="Version spécifique du modèle à analyser"),
    metric: Optional[str] = Query(None, description="Métrique spécifique pour le classement ou les analyses")
):
    """
    Get prediction accuracy analytics with comprehensive performance metrics.
    Implements never-empty contract by serving cached/latest data if live computation fails.
    """
    try:
        def compute_analytics():
            """Compute fresh prediction accuracy analytics"""
            try:
                return prediction_analyzer_service.get_prediction_accuracy_report(
                    tickers=ticker,
                    horizon=horizon,
                    days_back=days_back,
                    model_version=model_version
                )["data"]
            except Exception as e:
                print(f"Error in prediction analytics computation: {str(e)}")
                
                # Return fallback structure to maintain never-empty contract
                return {
                    "overall_metrics": {
                        "hit_rate": 0.0,
                        "accuracy": 0.0,
                        "precision": 0.0,
                        "recall": 0.0,
                        "f1_score": 0.0,
                        "mean_absolute_error": 0.0,
                        "root_mean_squared_error": 0.0,
                        "tracking_error": 0.0,
                        "correlation": 0.0,
                        "sharpe_ratio": 0.0,
                        "sample_size": 0,
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "message": "Prediction accuracy calculation failed, using fallback to maintain never-empty contract"
                    },
                    "by_ticker": {},
                    "by_horizon": {},
                    "prediction_count": 0,
                    "analysis_period": {
                        "days_back": days_back,
                        "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z", 
                        "end_date": datetime.utcnow().isoformat() + "Z"
                    },
                    "filters_applied": {
                        "tickers": ticker,
                        "horizon": horizon,
                        "model_version": model_version,
                        "days_back": days_back
                    },
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["prediction_analytics_route", "error_fallback", "fc-api-031"],
                    "error": str(e),
                    "message": "Prediction analytics computation failed but fallback data generated to maintain never-empty contract"
                }
        
        # Use cache layer to serve latest available data, compute fresh if none available
        cache_key = f"prediction_analytics_{'_'.join(sorted([t.upper() for t in ticker or []]))}_{horizon or 'all'}_{days_back}d_{model_version or 'all'}"
        analytics_data = load_or_compute(
            key=cache_key,
            compute_fn=compute_analytics,
            source=["prediction_analytics_route", "accuracy_calculation", "fc-api-031"]
        )
        
        # Ensure proper response format
        if not isinstance(analytics_data, dict):
            analytics_data = {
                "overall_metrics": {
                    "hit_rate": 0.0,
                    "accuracy": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0,
                    "mean_absolute_error": 0.0,
                    "root_mean_squared_error": 0.0,
                    "tracking_error": 0.0,
                    "correlation": 0.0,
                    "sharpe_ratio": 0.0,
                    "sample_size": 0,
                    "generated_at": datetime.utcnow().isoformat() + "Z"
                },
                "by_ticker": {},
                "by_horizon": {},
                "prediction_count": 0,
                "analysis_period": {
                    "days_back": days_back,
                    "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                    "end_date": datetime.utcnow().isoformat() + "Z"
                },
                "filters_applied": {
                    "tickers": ticker,
                    "horizon": horizon,
                    "model_version": model_version,
                    "days_back": days_back
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "message": "Analytics data format was invalid, using fallback to maintain never-empty contract"
            }
        
        return {
            "ok": True,  # Always true to maintain never-empty contract
            "data": analytics_data,
            "freshness": analytics_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
        
    except Exception as e:
        print(f"Error in /analytics/predictions endpoint: {str(e)}")
        
        # Return fallback to maintain never-empty contract
        return {
            "ok": True,  # Still return True to maintain never-empty contract
            "data": {
                "overall_metrics": {
                    "hit_rate": 0.0,
                    "accuracy": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0,
                    "mean_absolute_error": 0.0,
                    "root_mean_squared_error": 0.0,
                    "tracking_error": 0.0,
                    "correlation": 0.0,
                    "sharpe_ratio": 0.0,
                    "sample_size": 0,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e),
                    "message": "Prediction analytics endpoint failed but fallback data returned to maintain never-empty contract"
                },
                "by_ticker": {},
                "by_horizon": {},
                "prediction_count": 0,
                "analysis_period": {
                    "days_back": days_back,
                    "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                    "end_date": datetime.utcnow().isoformat() + "Z"
                },
                "filters_applied": {
                    "tickers": ticker,
                    "horizon": horizon,
                    "model_version": model_version,
                    "days_back": days_back
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["prediction_analytics_route", "endpoint_fallback", "fc-api-031"]
            },
            "freshness": "error"
        }

@router.get("/analytics/predictions/trends")
async def prediction_trends(
    ticker: Optional[str] = Query(None, description="Ticker spécifique pour l'analyse de tendance"),
    days_back: int = Query(90, ge=7, le=365, description="Nombre de jours pour l'analyse de tendance"),
    granularity: str = Query("weekly", description="Granularité pour l'analyse (daily, weekly, monthly)")
):
    """
    Get prediction accuracy trend analysis over time.
    Shows how model performance has evolved.
    """
    try:
        def compute_trend_data():
            """Compute fresh trend analysis"""
            try:
                from services.prediction_analyzer import get_prediction_trends
                return get_prediction_trends(ticker, days_back, granularity)["data"]
            except Exception as e:
                print(f"Error in prediction trends: {str(e)}")
                
                # Fallback trend data
                return {
                    "trend_analysis": {
                        "period": f"last_{days_back}_days",
                        "granularity": granularity,
                        "data_points": [],
                        "summary": {
                            "improvement_trend": "unknown",
                            "consistency_score": 0.0,
                            "recent_performance_change": 0.0
                        },
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["prediction_trends_route", "error_fallback", "fc-api-031"],
                        "error": str(e),
                        "message": "Prediction trend analysis failed but fallback returned to maintain never-empty contract"
                    }
                }
        
        trend_key = f"prediction_trends_{ticker or 'all'}_{days_back}d_{granularity}"
        trend_data = load_or_compute(
            key=trend_key,
            compute_fn=compute_trend_data,
            source=["prediction_trends_route", "trend_analysis", "fc-api-031"]
        )
        
        return {
            "ok": True,
            "data": trend_data,
            "freshness": trend_data.get("trend_analysis", {}).get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
        
    except Exception as e:
        print(f"Error in /analytics/predictions/trends endpoint: {str(e)}")
        
        return {
            "ok": True,
            "data": {
                "trend_analysis": {
                    "period": f"last_{days_back}_days",
                    "granularity": granularity,
                    "data_points": [],
                    "summary": {
                        "improvement_trend": "unknown",
                        "consistency_score": 0.0,
                        "recent_performance_change": 0.0
                    },
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e),
                    "message": "Prediction trends endpoint failed but fallback data returned to maintain never-empty contract"
                }
            },
            "freshness": "error"
        }

@router.get("/analytics/predictions/compare")
async def compare_prediction_models(
    model: List[str] = Query(..., description="Versions de modèle à comparer (ex: v1.0,v1.1,v1.2)"),
    ticker: List[str] = Query(None, description="Tickers à inclure dans la comparaison"),
    days_back: int = Query(30, ge=1, le=365, description="Nombre de jours d'historique pour la comparaison")
):
    """
    Compare prediction accuracy between different model versions.
    Useful for A/B testing and model improvement tracking.
    """
    try:
        def compute_model_comparison():
            """Compute fresh model comparison"""
            try:
                from services.prediction_analyzer import compare_prediction_models
                return compare_prediction_models(model, ticker, days_back)["data"]
            except Exception as e:
                print(f"Error in model comparison: {str(e)}")
                
                # Fallback comparison data
                return {
                    "model_comparisons": {
                        v: {
                            "hit_rate": 0.0,
                            "accuracy": 0.0,
                            "precision": 0.0,
                            "recall": 0.0,
                            "f1_score": 0.0,
                            "sharpe_ratio": 0.0,
                            "sample_size": 0,
                            "generated_at": datetime.utcnow().isoformat() + "Z"
                        } for v in model
                    },
                    "comparison_summary": {
                        "best_model_by_metric": {},
                        "model_rankings": {},
                        "comparison_metrics": ["hit_rate", "accuracy", "precision", "recall", "f1_score", "sharpe_ratio"]
                    },
                    "compared_versions": model,
                    "analysis_period": {
                        "days_back": days_back,
                        "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                        "end_date": datetime.utcnow().isoformat() + "Z"
                    },
                    "filters_applied": {"tickers": ticker},
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["model_comparison_route", "error_fallback", "fc-api-031"],
                    "error": str(e),
                    "message": "Model comparison failed but fallback data returned to maintain never-empty contract"
                }
        
        comparison_key = f"model_comparison_{'_'.join(sorted(model))}_{'_'.join(sorted([t.upper() for t in ticker or []])) if ticker else 'all'}_{days_back}d"
        comparison_data = load_or_compute(
            key=comparison_key,
            compute_fn=compute_model_comparison,
            source=["model_comparison_route", "accuracy_comparison", "fc-api-031"]
        )
        
        return {
            "ok": True,
            "data": comparison_data,
            "freshness": comparison_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
        
    except Exception as e:
        print(f"Error in /analytics/predictions/compare endpoint: {str(e)}")
        
        return {
            "ok": True,
            "data": {
                "model_comparisons": {
                    v: {
                        "hit_rate": 0.0,
                        "accuracy": 0.0,
                        "precision": 0.0,
                        "recall": 0.0,
                        "f1_score": 0.0,
                        "sharpe_ratio": 0.0,
                        "sample_size": 0,
                        "generated_at": datetime.utcnow().isoformat() + "Z"
                    } for v in model
                },
                "comparison_summary": {
                    "best_model_by_metric": {},
                    "model_rankings": {},
                    "comparison_metrics": ["hit_rate", "accuracy", "precision", "recall", "f1_score", "sharpe_ratio"]
                },
                "compared_versions": model,
                "analysis_period": {
                    "days_back": days_back,
                    "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                    "end_date": datetime.utcnow().isoformat() + "Z"
                },
                "filters_applied": {"tickers": ticker},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "message": "Model comparison endpoint failed but fallback data returned to maintain never-empty contract"
            },
            "freshness": "error"
        }