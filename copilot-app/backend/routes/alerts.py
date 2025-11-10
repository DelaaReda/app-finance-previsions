"""
Alert Rules Configuration API Routes
Task: FC-API-034 - Alert Rules Configuration
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from services.alert_rules import alert_rules_service
from models.alert_configuration import AlertType
from services.cache_layer import load_or_compute


router = APIRouter(prefix="/api", tags=["alerts"])

@router.get("/alerts/rules")
async def get_alert_rules(
    ticker: Optional[str] = Query(None, description="Filtre par ticker (ex: NVDA)"),
    alert_type: Optional[str] = Query(None, description="Filtre par type d'alerte"),
    enabled: Optional[bool] = Query(None, description="Filtre par statut d'activation"),
    priority: Optional[str] = Query(None, description="Filtre par priorité (low, medium, high, critical)")
):
    """
    Get list of configured alert rules with filtering options.
    Implements never-empty contract by serving cached/latest data if live computation fails.
    """
    try:
        def compute_alerts():
            """Compute fresh alert rules data"""
            try:
                # Convert string alert type to enum if provided
                type_filter = None
                if alert_type:
                    try:
                        type_filter = AlertType(alert_type.lower())
                    except ValueError:
                        # If invalid enum, continue without type filter
                        type_filter = None
                
                # Get alert rules with filtering
                return alert_rules_service.get_all_alert_rules(
                    ticker_filter=ticker,
                    type_filter=type_filter,
                    enabled_only=(enabled if enabled is not None else True)
                )
            except Exception as e:
                print(f"Error computing alert rules: {str(e)}")
                
                # Return fallback to maintain never-empty contract
                return {
                    "ok": True,
                    "data": {
                        "rules": [],
                        "total_count": 0,
                        "filters_applied": {
                            "ticker": ticker,
                            "alert_type": alert_type,
                            "enabled": enabled,
                            "priority": priority
                        },
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["alerts_rules_route", "error_fallback", "fc-api-034"],
                        "message": "Alert rules retrieval failed but fallback returned to maintain never-empty contract"
                    },
                    "freshness": "error"
                }
        
        # Use cache layer to serve latest available data
        cache_key = f"alerts_rules_{ticker or 'all'}_{alert_type or 'all'}_{enabled}_{priority or 'all'}"
        alerts_result = load_or_compute(
            key=cache_key,
            compute_fn=compute_alerts,
            source=["alerts_rules_route", "rule_listing", "fc-api-034"]
        )
        
        return alerts_result
        
    except Exception as e:
        print(f"Error in /alerts/rules endpoint: {str(e)}")
        
        # Return structured fallback to maintain never-empty contract
        return {
            "ok": True,  # Maintain never-empty contract
            "data": {
                "rules": [],
                "total_count": 0,
                "filters_applied": {
                    "ticker": ticker,
                    "alert_type": alert_type,
                    "enabled": enabled,
                    "priority": priority
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["alerts_rules_route", "error_fallback", "fc-api-034"],
                "error": str(e),
                "message": "Alert rules endpoint failed but fallback data returned to maintain never-empty contract"
            },
            "freshness": "error"
        }


@router.post("/alerts/rules")
async def create_alert_rule(
    name: str = Query(..., description="Nom de la règle d'alerte"),
    description: str = Query("", description="Description de la règle"),
    alert_type: str = Query(..., description="Type de l'alerte"),
    tickers: List[str] = Query(..., description="Liste des tickers concernés (ex: NVDA,AAPL,MSFT)"),
    condition_field: str = Query(..., description="Champ à surveiller (ex: price_change, rsi, volatility)"),
    condition_operator: str = Query(..., description="Opérateur de comparaison (gt, lt, gte, lte, eq, ne)"),
    condition_value: float = Query(..., description="Valeur seuil pour la condition"),
    enabled: bool = Query(True, description="Statut d'activation de la règle"),
    priority: str = Query("medium", description="Priorité (low, medium, high, critical)"),
    delivery_methods: str = Query("email,push", description="Méthodes de livraison (séparées par virgule)"),
    frequency: str = Query("realtime", description="Fréquence (realtime, hourly, daily, weekly)"),
    cooldown_minutes: int = Query(5, ge=0, le=1440, description="Minutes de cooldown entre alertes (min 0, max 1440)")
):
    """
    Create a new alert rule with validation and persistence.
    """
    try:
        # Parse delivery methods from comma-separated string
        delivery_methods_list = [dm.strip() for dm in delivery_methods.split(",")]
        
        # Create the alert rule through the service
        result = alert_rules_service.create_alert_rule(
            name=name,
            description=description,
            alert_type=alert_type,
            tickers=tickers,
            condition_field=condition_field,
            condition_operator=condition_operator,
            condition_value=condition_value,
            enabled=enabled,
            priority=priority,
            delivery_methods=delivery_methods_list,
            frequency=frequency,
            cooldown_minutes=cooldown_minutes
        )
        
        return result
        
    except Exception as e:
        print(f"Error in /alerts/rules creation: {str(e)}")
        
        return {
            "ok": False,
            "data": {
                "rule": None,
                "message": f"Alert rule creation failed: {str(e)}, but system remains operational",
                "error": str(e),
                "source": ["alerts_rules_route", "creation_error_fallback", "fc-api-034"]
            },
            "freshness": "error"
        }


@router.put("/alerts/rules/{rule_id}")
async def update_alert_rule(rule_id: str, updates: Dict[str, Any]):
    """
    Update an existing alert rule with validation.
    """
    try:
        result = alert_rules_service.update_alert_rule(rule_id, updates)
        return result
    except Exception as e:
        print(f"Error updating alert rule {rule_id}: {str(e)}")
        
        return {
            "ok": False,
            "data": {
                "success": False,
                "message": f"Alert rule update failed: {str(e)}, but system remains operational",
                "error": str(e),
                "source": ["alerts_rules_route", "update_error_fallback", "fc-api-034"]
            },
            "freshness": "error"
        }


@router.delete("/alerts/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """
    Delete an alert rule by ID.
    """
    try:
        result = alert_rules_service.delete_alert_rule(rule_id)
        return result
    except Exception as e:
        print(f"Error deleting alert rule {rule_id}: {str(e)}")
        
        return {
            "ok": False,
            "data": {
                "success": False,
                "message": f"Alert rule deletion failed: {str(e)}, but system remains operational",
                "error": str(e),
                "source": ["alerts_rules_route", "deletion_error_fallback", "fc-api-034"]
            },
            "freshness": "error"
        }


@router.get("/alerts/types")
async def get_alert_types():
    """
    Get available alert types for UI selection.
    """
    try:
        result = alert_rules_service.get_alert_types_options()
        return result
    except Exception as e:
        print(f"Error getting alert types: {str(e)}")
        
        return {
            "ok": True,  # Maintain never-empty contract
            "data": {
                "alert_types": [atype.value for atype in AlertType],
                "descriptions": {
                    "price_change": "Price movement alerts",
                    "volatility_spike": "Volatility threshold alerts",
                    "technical_breakout": "Technical indicator breakout alerts",
                    "news_sentiment": "News sentiment based alerts",
                    "rsi_oversold_overbought": "RSI oversold/overbought alerts",
                    "moving_average_cross": "Moving average crossover alerts",
                    "earnings_surprise": "Earnings surprise alerts",
                    "macro_impact": "Macro economic impact alerts",
                    "volume_spike": "Unusual volume alerts",
                    "beta_adjustment": "Beta change alerts"
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["alerts_rules_route", "types_options", "fc-api-034"],
                "error": str(e),
                "message": "Alert types retrieval failed but fallback returned to maintain never-empty contract"
            },
            "freshness": "error"
        }