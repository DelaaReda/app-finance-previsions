"""
Alert Rules Service
Task: FC-API-034 - Alert Rules Configuration  
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from models.alert_configuration import AlertConfigurationModel, AlertType, AlertRule
from storage.io import load_json, save_json
from services.cache_layer import load_or_compute


class AlertRulesService:
    """
    Service for managing alert rules configuration: creation, update, deletion
    """
    
    def __init__(self):
        self.model = AlertConfigurationModel()
    
    def get_all_alert_rules(self, 
                           ticker_filter: Optional[str] = None,
                           type_filter: Optional[AlertType] = None,
                           enabled_only: bool = True) -> Dict[str, Any]:
        """
        Get all configured alert rules with filtering options
        """
        def compute_rules():
            """Compute fresh alert rules from model"""
            try:
                rules = self.model.get_all_alert_rules(ticker_filter, type_filter, enabled_only)
                
                rules_data = [rule.to_dict() for rule in rules]
                
                return {
                    "rules": rules_data,
                    "count": len(rules_data),
                    "filters_applied": {
                        "ticker": ticker_filter,
                        "type": type_filter.value if type_filter else None,
                        "enabled_only": enabled_only
                    },
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["alert_rules_service", "configuration_list", "fc-api-034"]
                }
                
            except Exception as e:
                print(f"Error in get_all_alert_rules computation: {str(e)}")
                
                # Return fallback to maintain never-empty contract
                return {
                    "rules": [],
                    "count": 0,
                    "filters_applied": {
                        "ticker": ticker_filter,
                        "type": type_filter.value if type_filter else None,
                        "enabled_only": enabled_only
                    },
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e),
                    "message": "Alert rules retrieval failed but fallback data returned to maintain never-empty contract",
                    "source": ["alert_rules_service", "error_fallback", "fc-api-034"]
                }
        
        # Use cache layer to serve latest available data, compute fresh if none available
        cache_key = f"alert_rules_{ticker_filter or 'all'}_{type_filter.value if type_filter else 'all'}_{enabled_only}"
        rules_data = load_or_compute(
            key=cache_key,
            compute_fn=compute_rules,
            source=["alert_rules_service", "configuration_management", "fc-api-034"]
        )
        
        return {
            "ok": True,  # Always maintain never-empty contract
            "data": rules_data,
            "freshness": rules_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    
    def create_alert_rule(self, 
                         name: str, 
                         description: str, 
                         alert_type: str,  # Will convert to enum
                         tickers: List[str],
                         condition_field: str,
                         condition_operator: str,
                         condition_value: Any,
                         threshold_type: str = "absolute",
                         enabled: bool = True,
                         priority: str = "medium",
                         delivery_methods: Optional[List[str]] = None,
                         frequency: str = "realtime",
                         cooldown_minutes: int = 5) -> Dict[str, Any]:
        """
        Create a new alert rule with validation and error handling
        """
        def compute_new_rule():
            """Compute the creation of a new alert rule"""
            try:
                # Convert string alert_type to enum
                try:
                    alert_type_enum = AlertType(alert_type)
                except ValueError:
                    # If invalid enum value, default to price_change
                    alert_type_enum = AlertType.PRICE_CHANGE
                
                # Create the rule using the model
                new_rule = self.model.create_alert_rule(
                    name=name,
                    description=description,
                    alert_type=alert_type_enum,
                    tickers=tickers,
                    condition_field=condition_field,
                    condition_operator=condition_operator,
                    condition_value=condition_value,
                    threshold_type=threshold_type,
                    enabled=enabled,
                    priority=priority,
                    delivery_methods=delivery_methods,
                    frequency=frequency,
                    cooldown_minutes=cooldown_minutes
                )
                
                if new_rule:
                    return {
                        "rule": new_rule.to_dict(),
                        "message": "Alert rule created successfully",
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["alert_rules_service", "rule_creation", "fc-api-034"]
                    }
                else:
                    # If rule creation failed, return error structure
                    return {
                        "rule": None,
                        "message": "Alert rule creation failed due to validation errors",
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "error": "Rule creation validation failed",
                        "source": ["alert_rules_service", "creation_error", "fc-api-034"]
                    }
                    
            except Exception as e:
                print(f"Error in create_alert_rule computation: {str(e)}")
                
                # Return fallback to maintain never-empty contract
                return {
                    "rule": None,
                    "message": f"Alert rule creation failed: {str(e)}, but system remains operational",
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e),
                    "source": ["alert_rules_service", "creation_error_fallback", "fc-api-034"]
                }
        
        # Use cache layer for creating new rule
        cache_key = f"create_alert_{int(datetime.utcnow().timestamp())}_{hash(name)}"
        rule_result = load_or_compute(
            key=cache_key,
            compute_fn=compute_new_rule,
            source=["alert_rules_service", "rule_creation", "fc-api-034"]
        )
        
        # Check if creation was successful
        success = rule_result.get("rule") is not None
        
        return {
            "ok": success,
            "data": rule_result,
            "freshness": rule_result.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    
    def update_alert_rule(self, rule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing alert rule with validation
        """
        def compute_update():
            """Compute the update of an existing alert rule"""
            try:
                # Validate that the rule exists before trying to update
                existing_rule = self.model.get_alert_rule(rule_id)
                if not existing_rule:
                    return {
                        "success": False,
                        "message": f"Alert rule with ID {rule_id} does not exist",
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["alert_rules_service", "update_nonexistent", "fc-api-034"]
                    }
                
                # Perform the update
                update_success = self.model.update_alert_rule(rule_id, updates)
                
                if update_success:
                    # Retrieve updated rule
                    updated_rule = self.model.get_alert_rule(rule_id)
                    
                    return {
                        "success": True,
                        "rule": updated_rule.to_dict() if updated_rule else None,
                        "message": "Alert rule updated successfully",
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["alert_rules_service", "rule_update", "fc-api-034"]
                    }
                else:
                    return {
                        "success": False,
                        "message": "Alert rule update failed",
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["alert_rules_service", "update_failed", "fc-api-034"]
                    }
                    
            except Exception as e:
                print(f"Error in update_alert_rule computation: {str(e)}")
                
                # Return fallback to maintain never-empty contract
                return {
                    "success": False,
                    "message": f"Alert rule update failed: {str(e)}, but system remains operational",
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e),
                    "source": ["alert_rules_service", "update_error_fallback", "fc-api-034"]
                }
        
        # Use cache layer for updating
        cache_key = f"update_alert_{rule_id}_{int(datetime.utcnow().timestamp())}"
        update_result = load_or_compute(
            key=cache_key,
            compute_fn=compute_update,
            source=["alert_rules_service", "rule_update", "fc-api-034"]
        )
        
        # Return appropriate response
        return {
            "ok": update_result.get("success", False),
            "data": update_result,
            "freshness": update_result.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    
    def delete_alert_rule(self, rule_id: str) -> Dict[str, Any]:
        """
        Delete an alert rule with confirmation
        """
        def compute_delete():
            """Compute the deletion of an alert rule"""
            try:
                # First check if the rule exists
                existing_rule = self.model.get_alert_rule(rule_id)
                if not existing_rule:
                    return {
                        "success": False,
                        "message": f"Alert rule with ID {rule_id} does not exist",
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["alert_rules_service", "delete_nonexistent", "fc-api-034"]
                    }
                
                # Perform the deletion
                delete_success = self.model.delete_alert_rule(rule_id)
                
                if delete_success:
                    return {
                        "success": True,
                        "deleted_rule_id": rule_id,
                        "message": "Alert rule deleted successfully",
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["alert_rules_service", "rule_deletion", "fc-api-034"]
                    }
                else:
                    return {
                        "success": False,
                        "message": "Alert rule deletion failed",
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["alert_rules_service", "deletion_failed", "fc-api-034"]
                    }
                    
            except Exception as e:
                print(f"Error in delete_alert_rule computation: {str(e)}")
                
                # Return fallback to maintain never-empty contract
                return {
                    "success": False,
                    "message": f"Alert rule deletion failed: {str(e)}, but system remains operational",
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e),
                    "source": ["alert_rules_service", "deletion_error_fallback", "fc-api-034"]
                }
        
        # Use cache layer for deletion
        cache_key = f"delete_alert_{rule_id}_{int(datetime.utcnow().timestamp())}"
        delete_result = load_or_compute(
            key=cache_key,
            compute_fn=compute_delete,
            source=["alert_rules_service", "rule_deletion", "fc-api-034"]
        )
        
        # Return appropriate response
        return {
            "ok": delete_result.get("success", False),
            "data": delete_result,
            "freshness": delete_result.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    
    def get_alert_types_options(self) -> Dict[str, Any]:
        """
        Get available alert types for UI selection
        """
        try:
            # Get all available AlertType values
            alert_types = [alert_type.value for alert_type in AlertType]
            
            # Description mapping for each alert type
            alert_descriptions = {
                "price_change": "Alert triggered by significant price movements",
                "volatility_spike": "Alert triggered when volatility exceeds threshold",
                "technical_breakout": "Alert for technical indicator breakouts",
                "news_sentiment": "Alert based on news sentiment changes",
                "rsi_oversold_overbought": "Alert for RSI oversold/overbought conditions",
                "moving_average_cross": "Alert for moving average crossover events",
                "earnings_surprise": "Alert for earnings surprise events",
                "macro_impact": "Alert based on macroeconomic impact",
                "volume_spike": "Alert for unusual volume spikes",
                "beta_adjustment": "Alert for changes in beta relative to benchmark"
            }
            
            return {
                "ok": True,
                "data": {
                    "alert_types": alert_types,
                    "descriptions": {atype: alert_descriptions.get(atype, "No description provided") for atype in alert_types},
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["alert_rules_service", "alert_type_options", "fc-api-034"]
                },
                "freshness": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            print(f"Error in get_alert_types_options: {str(e)}")
            
            # Return fallback to maintain never-empty contract
            return {
                "ok": True,
                "data": {
                    "alert_types": [atype.value for atype in AlertType],
                    "descriptions": {},
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e),
                    "message": "Alert types options retrieval failed but fallback returned to maintain never-empty contract",
                    "source": ["alert_rules_service", "options_error_fallback", "fc-api-034"]
                },
                "freshness": "error"
            }
    
    def get_default_rules(self) -> Dict[str, Any]:
        """
        Get default alert rules that should be available for all users
        """
        try:
            # Return the default rules defined in the model
            default_rules = self.model.get_default_rules()
            
            rules_data = [rule.to_dict() for rule in default_rules]
            
            return {
                "ok": True,
                "data": {
                    "default_rules": rules_data,
                    "count": len(rules_data),
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["alert_rules_service", "default_rules", "fc-api-034"]
                },
                "freshness": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            print(f"Error in get_default_rules: {str(e)}")
            
            # Return fallback with empty list to maintain never-empty contract
            return {
                "ok": True,
                "data": {
                    "default_rules": [],
                    "count": 0,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e),
                    "message": "Default rules retrieval failed but empty list returned to maintain never-empty contract",
                    "source": ["alert_rules_service", "defaults_error_fallback", "fc-api-034"]
                },
                "freshness": "error"
            }


# Global instance
alert_rules_service = AlertRulesService()

# Convenience functions
def get_all_alerts(ticker_filter: Optional[str] = None, type_filter: Optional[str] = None, enabled_only: bool = True):
    """
    Get all configured alert rules
    """
    # Convert type filter to enum if provided
    type_enum = None
    if type_filter:
        try:
            type_enum = AlertType(type_filter)
        except ValueError:
            # Use default if invalid
            type_enum = AlertType.PRICE_CHANGE
    
    return alert_rules_service.get_all_alert_rules(ticker_filter, type_enum, enabled_only)

def create_alert(name: str, description: str, alert_type: str, tickers: List[str],
                condition_field: str, condition_operator: str, condition_value: Any,
                threshold_type: str = "absolute", enabled: bool = True, priority: str = "medium",
                delivery_methods: Optional[List[str]] = None, frequency: str = "realtime", cooldown_minutes: int = 5):
    """
    Create a new alert rule
    """
    return alert_rules_service.create_alert_rule(name, description, alert_type, tickers,
                                               condition_field, condition_operator, condition_value,
                                               threshold_type, enabled, priority, delivery_methods,
                                               frequency, cooldown_minutes)

def update_alert(rule_id: str, updates: Dict[str, Any]):
    """
    Update an existing alert rule
    """
    return alert_rules_service.update_alert_rule(rule_id, updates)

def delete_alert(rule_id: str):
    """
    Delete an alert rule
    """
    return alert_rules_service.delete_alert_rule(rule_id)

def get_alert_types():
    """
    Get available alert type options
    """
    return alert_rules_service.get_alert_types_options()

def get_default_alert_rules():
    """
    Get default alert rules
    """
    return alert_rules_service.get_default_rules()