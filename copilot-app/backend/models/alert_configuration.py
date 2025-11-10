"""
Alert Configuration Model
Task: FC-API-034 - Alert Rules Configuration
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from storage.io import load_json, save_json
from services.cache_layer import load_or_compute


class AlertType(Enum):
    """
    Types of alerts supported by the system
    """
    PRICE_CHANGE = "price_change"
    VOLATILITY_SPIKE = "volatility_spike"
    TECHNICAL_BREAKOUT = "technical_breakout"
    NEWS_SENTIMENT = "news_sentiment"
    RSI_OVERSOLD_OVERBOUGHT = "rsi_oversold_overbought"
    MOVING_AVERAGE_CROSS = "moving_average_cross"
    EARNINGS_SURPRISE = "earnings_surprise"
    MACRO_IMPACT = "macro_impact"
    VOLUME_SPIKE = "volume_spike"
    BETA_ADJUSTMENT = "beta_adjustment"


class AlertCondition:
    """
    Condition for triggering an alert
    """
    
    def __init__(self, 
                 field: str, 
                 operator: str, 
                 value: Union[float, str, int],
                 threshold_type: str = "absolute"):
        self.field = field
        self.operator = operator  # gt, lt, eq, gte, lte, in_range, crosses_above, crosses_below
        self.value = value
        self.threshold_type = threshold_type
        self.created_at = datetime.utcnow().isoformat() + "Z"


class AlertRule:
    """
    Model representing a single alert rule
    """
    
    def __init__(self, 
                 id: str, 
                 name: str, 
                 description: str,
                 alert_type: AlertType,
                 tickers: List[str],
                 condition: AlertCondition,
                 enabled: bool = True,
                 priority: str = "medium",  # low, medium, high, critical
                 delivery_methods: List[str] = None,  # email, push, sms, webhook
                 frequency: str = "realtime",  # realtime, hourly, daily, weekly
                 cooldown_minutes: int = 5,
                 source: str = "user_defined"):
        self.id = id
        self.name = name
        self.description = description
        self.alert_type = alert_type
        self.tickers = [t.upper() for t in tickers]  # Normalize to uppercase
        self.condition = condition
        self.enabled = enabled
        self.priority = priority
        self.delivery_methods = delivery_methods or ["email", "push"]
        self.frequency = frequency
        self.cooldown_minutes = cooldown_minutes
        self.source = source
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        self.last_triggered = None
        self.trigger_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "alert_type": self.alert_type.value,
            "tickers": self.tickers,
            "condition": {
                "field": self.condition.field,
                "operator": self.condition.operator,
                "value": self.condition.value,
                "threshold_type": self.condition.threshold_type
            },
            "enabled": self.enabled,
            "priority": self.priority,
            "delivery_methods": self.delivery_methods,
            "frequency": self.frequency,
            "cooldown_minutes": self.cooldown_minutes,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_triggered": self.last_triggered,
            "trigger_count": self.trigger_count
        }
    
    def evaluate_condition(self, asset_data: Dict[str, Any]) -> bool:
        """
        Evaluate if the alert condition is met based on asset data
        
        Args:
            asset_data: Asset data containing relevant values for evaluation
            
        Returns:
            True if condition is met, False otherwise
        """
        try:
            # Get the field value from asset data
            current_value = None
            if self.condition.field in asset_data:
                current_value = asset_data[self.condition.field]
            elif f"current_{self.condition.field}" in asset_data:
                current_value = asset_data[f"current_{self.condition.field}"]
            elif self.condition.field.replace("_change", "_percent_change") in asset_data:
                current_value = asset_data.get(self.condition.field, 0)
            else:
                # Try to get from nested structures (common in financial data)
                current_value = self._get_nested_value(asset_data, self.condition.field)
            
            if current_value is None:
                # If no value available, condition not met (don't trigger alert)
                return False
            
            # Compare based on operator
            if self.condition.operator == "gt":
                return current_value > self.condition.value
            elif self.condition.operator == "lt":  
                return current_value < self.condition.value
            elif self.condition.operator == "gte":
                return current_value >= self.condition.value
            elif self.condition.operator == "lte":
                return current_value <= self.condition.value
            elif self.condition.operator == "eq":
                return current_value == self.condition.value
            elif self.condition.operator == "ne":
                return current_value != self.condition.value
            elif self.condition.operator == "crosses_above":
                # Used for technical indicators like RSI crossing above threshold
                prev_value = asset_data.get(f"prev_{self.condition.field}", current_value)
                return prev_value <= self.condition.value and current_value > self.condition.value
            elif self.condition.operator == "crosses_below":
                # Used for technical indicators like RSI crossing below threshold
                prev_value = asset_data.get(f"prev_{self.condition.field}", current_value)
                return prev_value >= self.condition.value and current_value < self.condition.value
            elif self.condition.operator == "out_of_range":
                # For values that should stay within a range
                if isinstance(self.condition.value, (list, tuple)) and len(self.condition.value) == 2:
                    return current_value < self.condition.value[0] or current_value > self.condition.value[1]
                else:
                    return False  # Invalid range
            elif self.condition.operator == "in_range":
                # For values that should stay within a range
                if isinstance(self.condition.value, (list, tuple)) and len(self.condition.value) == 2:
                    return self.condition.value[0] <= current_value <= self.condition.value[1]
                else:
                    return False  # Invalid range
            else:
                # For unknown operators, don't trigger alert
                return False
                
        except Exception as e:
            print(f"Error evaluating condition for alert {self.id}: {str(e)}")
            # Don't trigger alert if evaluation fails (safety default)
            return False
    
    def _get_nested_value(self, data: Dict, field_path: str) -> Any:
        """
        Get value from nested data structure using dot notation path.
        
        Args:
            data: Dictionary of data
            field_path: Dot-notation path (e.g., "tech_indicators.rsi.current_value")
            
        Returns:
            Value at path or None if not found
        """
        try:
            parts = field_path.split('.')
            current = data
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            
            return current
        except:
            return None


class AlertConfigurationModel:
    """
    Model for managing alert configurations and rules
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.rules = {}
        self.data_dir = Path(__file__).resolve().parent / "data" / "alerts"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing rules from storage
        self._load_existing_rules()
    
    def _load_existing_rules(self):
        """
        Load existing alert rules from persistent storage
        """
        try:
            rules_data = load_json(f"alerts/rules_{self.user_id}") or {}
            saved_rules = rules_data.get("rules", [])
            
            for rule_dict in saved_rules:
                rule = self._dict_to_rule(rule_dict)
                if rule:
                    self.rules[rule.id] = rule
                    
        except Exception as e:
            print(f"Error loading alert rules from storage: {str(e)}")
            # Continue with empty rules if loading fails
    
    def _dict_to_rule(self, rule_dict: Dict[str, Any]) -> Optional[AlertRule]:
        """
        Convert dictionary representation to AlertRule object
        """
        try:
            # Create condition object
            condition_data = rule_dict["condition"]
            condition = AlertCondition(
                field=condition_data["field"],
                operator=condition_data["operator"],
                value=condition_data["value"],
                threshold_type=condition_data.get("threshold_type", "absolute")
            )
            
            # Convert alert type string back to enum
            try:
                alert_type = AlertType(rule_dict["alert_type"])
            except ValueError:
                # If invalid enum, use default
                alert_type = AlertType.PRICE_CHANGE
            
            rule = AlertRule(
                id=rule_dict["id"],
                name=rule_dict["name"],
                description=rule_dict["description"],
                alert_type=alert_type,
                tickers=rule_dict["tickers"],
                condition=condition,
                enabled=rule_dict.get("enabled", True),
                priority=rule_dict.get("priority", "medium"),
                delivery_methods=rule_dict.get("delivery_methods", ["email", "push"]),
                frequency=rule_dict.get("frequency", "realtime"),
                cooldown_minutes=rule_dict.get("cooldown_minutes", 5),
                source=rule_dict.get("source", "user_defined")
            )
            
            # Set additional properties
            rule.created_at = rule_dict.get("created_at", datetime.utcnow().isoformat() + "Z")
            rule.updated_at = rule_dict.get("updated_at", datetime.utcnow().isoformat() + "Z")
            rule.last_triggered = rule_dict.get("last_triggered")
            rule.trigger_count = rule_dict.get("trigger_count", 0)
            
            return rule
        except Exception as e:
            print(f"Error converting dict to rule: {str(e)}")
            return None
    
    def create_alert_rule(self, 
                         name: str, 
                         description: str, 
                         alert_type: AlertType,
                         tickers: List[str],
                         condition_field: str,
                         condition_operator: str,
                         condition_value: Union[float, str, int],
                         threshold_type: str = "absolute",
                         enabled: bool = True,
                         priority: str = "medium",
                         delivery_methods: Optional[List[str]] = None,
                         frequency: str = "realtime",
                         cooldown_minutes: int = 5) -> Optional[AlertRule]:
        """
        Create a new alert rule with validation
        """
        try:
            # Validate inputs
            if not name or not name.strip():
                raise ValueError("Alert rule name is required")
            
            if not tickers or len(tickers) == 0:
                raise ValueError("At least one ticker must be specified")
            
            # Validate tickers (simple format check)
            validated_tickers = []
            for ticker in tickers:
                if isinstance(ticker, str) and ticker.strip() and len(ticker) <= 10:
                    validated_tickers.append(ticker.upper().strip())
            
            if len(validated_tickers) == 0:
                raise ValueError("No valid tickers provided")
            
            # Validate operators
            valid_operators = ["gt", "lt", "gte", "lte", "eq", "ne", "crosses_above", "crosses_below", "in_range", "out_of_range"]
            if condition_operator not in valid_operators:
                raise ValueError(f"Invalid operator: {condition_operator}. Must be one of: {valid_operators}")
            
            # Validate priority
            valid_priorities = ["low", "medium", "high", "critical"]
            if priority not in valid_priorities:
                raise ValueError(f"Invalid priority: {priority}. Must be one of: {valid_priorities}")
            
            # Validate frequency
            valid_frequencies = ["realtime", "hourly", "daily", "weekly"]
            if frequency not in valid_frequencies:
                raise ValueError(f"Invalid frequency: {frequency}. Must be one of: {valid_frequencies}")
            
            # Validate cooldown
            cooldown_minutes = max(0, min(1440, cooldown_minutes))  # Max 24 hours
            
            # Create condition
            condition = AlertCondition(
                field=condition_field,
                operator=condition_operator,
                value=condition_value,
                threshold_type=threshold_type
            )
            
            # Create unique ID
            rule_id = f"alert_{self.user_id}_{int(datetime.utcnow().timestamp())}_{len(self.rules) + 1}"
            
            # Create rule
            rule = AlertRule(
                id=rule_id,
                name=name.strip(),
                description=description,
                alert_type=alert_type,
                tickers=validated_tickers,
                condition=condition,
                enabled=enabled,
                priority=priority,
                delivery_methods=delivery_methods or ["email", "push"],
                frequency=frequency,
                cooldown_minutes=cooldown_minutes,
                source="user_defined"
            )
            
            # Store in memory
            self.rules[rule_id] = rule
            
            # Persist to storage
            self._save_rules()
            
            return rule
            
        except Exception as e:
            print(f"Error creating alert rule: {str(e)}")
            return None
    
    def get_alert_rule(self, rule_id: str) -> Optional[AlertRule]:
        """
        Get a specific alert rule by ID
        """
        return self.rules.get(rule_id)
    
    def get_all_alert_rules(self, 
                           ticker_filter: Optional[str] = None,
                           type_filter: Optional[AlertType] = None,
                           enabled_only: bool = True) -> List[AlertRule]:
        """
        Get all alert rules with optional filtering
        """
        rules_list = []
        
        for rule in self.rules.values():
            # Apply filters
            if enabled_only and not rule.enabled:
                continue
            
            if ticker_filter and ticker_filter.upper() not in rule.tickers:
                continue
            
            if type_filter and rule.alert_type != type_filter:
                continue
            
            rules_list.append(rule)
        
        return rules_list
    
    def update_alert_rule(self, 
                         rule_id: str, 
                         updates: Dict[str, Any]) -> bool:
        """
        Update an existing alert rule
        """
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        
        # Apply updates with validation
        if "name" in updates and updates["name"]:
            rule.name = updates["name"].strip()
        
        if "description" in updates:
            rule.description = updates["description"]
        
        if "enabled" in updates:
            rule.enabled = bool(updates["enabled"])
        
        if "priority" in updates:
            valid_priorities = ["low", "medium", "high", "critical"]
            if updates["priority"] in valid_priorities:
                rule.priority = updates["priority"]
        
        if "delivery_methods" in updates:
            rule.delivery_methods = updates["delivery_methods"]
        
        if "frequency" in updates:
            valid_frequencies = ["realtime", "hourly", "daily", "weekly"]
            if updates["frequency"] in valid_frequencies:
                rule.frequency = updates["frequency"]
        
        if "cooldown_minutes" in updates:
            rule.cooldown_minutes = max(0, min(1440, int(updates["cooldown_minutes"])))  # Max 24 hours
        
        if "tickers" in updates and updates["tickers"]:
            # Validate and update tickers
            validated_tickers = []
            for ticker in updates["tickers"]:
                if isinstance(ticker, str) and ticker.strip() and len(ticker) <= 10:
                    validated_tickers.append(ticker.upper().strip())
            if validated_tickers:
                rule.tickers = validated_tickers
        
        # Update condition if provided
        if "condition" in updates:
            condition_data = updates["condition"]
            if isinstance(condition_data, dict) and all(k in condition_data for k in ["field", "operator", "value"]):
                rule.condition = AlertCondition(
                    field=condition_data["field"],
                    operator=condition_data["operator"],
                    value=condition_data["value"],
                    threshold_type=condition_data.get("threshold_type", "absolute")
                )
        
        # Update timestamp
        rule.updated_at = datetime.utcnow().isoformat() + "Z"
        
        # Persist changes
        self._save_rules()
        
        return True
    
    def delete_alert_rule(self, rule_id: str) -> bool:
        """
        Delete an alert rule
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            
            # Persist changes
            self._save_rules()
            
            return True
        
        return False
    
    def _save_rules(self):
        """
        Save all rules to persistent storage
        """
        try:
            # Convert rules to serializable format
            rules_list = [rule.to_dict() for rule in self.rules.values()]
            
            save_json(f"alerts/rules_{self.user_id}", {
                "rules": rules_list,
                "count": len(rules_list),
                "user_id": self.user_id,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["alert_configuration_model", "rules_persistence", "fc-api-034"]
            }, source=["alert_rules_model", "persistence", "fc-api-034"])
            
        except Exception as e:
            print(f"Error saving alert rules: {str(e)}")
            # Continue operation even if persistence fails (never-empty contract)
    
    def get_default_rules(self) -> List[AlertRule]:
        """
        Get default alert rules that should be available for all users
        """
        defaults = []
        
        try:
            # RSI Oversold Rule
            rsi_oversold_condition = AlertCondition("rsi", "lte", 30, "technical")
            rsi_oversold_rule = AlertRule(
                id=f"default_rsi_oversold_{self.user_id}",
                name="RSI Oversold Alert",
                description="Triggered when RSI drops below 30 (indicating oversold condition)",
                alert_type=AlertType.RSI_OVERSOLD_OVERBOUGHT,
                tickers=["SPY", "QQQ", "NVDA"],
                condition=rsi_oversold_condition,
                priority="high",
                delivery_methods=["email", "push"],
                frequency="realtime",
                cooldown_minutes=10
            )
            defaults.append(rsi_oversold_rule)
            
            # RSI Overbought Rule
            rsi_overbought_condition = AlertCondition("rsi", "gte", 70, "technical")
            rsi_overbought_rule = AlertRule(
                id=f"default_rsi_overbought_{self.user_id}",
                name="RSI Overbought Alert", 
                description="Triggered when RSI rises above 70 (indicating overbought condition)",
                alert_type=AlertType.RSI_OVERSOLD_OVERBOUGHT,
                tickers=["SPY", "QQQ", "NVDA"],
                condition=rsi_overbought_condition,
                priority="medium",
                delivery_methods=["email", "push"],
                frequency="realtime",
                cooldown_minutes=10
            )
            defaults.append(rsi_overbought_rule)
            
            # High volatility Rule
            vol_condition = AlertCondition("volatility", "gte", 0.03, "percentage")  # 3% daily volatility
            vol_rule = AlertRule(
                id=f"default_high_vol_{self.user_id}",
                name="High Volatility Alert",
                description="Triggered when volatility exceeds 3% daily",
                alert_type=AlertType.VOLATILITY_SPIKE,
                tickers=["SPY", "QQQ", "AAPL", "MSFT", "NVDA"],
                condition=vol_condition,
                priority="high",
                delivery_methods=["email", "push"],
                frequency="realtime",
                cooldown_minutes=5
            )
            defaults.append(vol_rule)
            
            # Price change Rule (significant movement)
            price_condition = AlertCondition("price_change_pct", "gte", 0.05)  # 5% move
            price_rule = AlertRule(
                id=f"default_price_move_{self.user_id}",
                name="Significant Price Movement Alert",
                description="Triggered when price moves more than 5%",
                alert_type=AlertType.PRICE_CHANGE,
                tickers=["SPY", "QQQ", "NVDA", "TSLA"],
                condition=price_condition,
                priority="medium",
                delivery_methods=["email", "push"],
                frequency="realtime",
                cooldown_minutes=30
            )
            defaults.append(price_rule)
            
        except Exception as e:
            print(f"Error creating default rules: {str(e)}")
            # Return minimal defaults if creation fails
            return []
        
        return defaults


# Global instance with default user
alert_config_model = AlertConfigurationModel()


# Convenience functions
def create_alert_rule(name: str, description: str, alert_type: AlertType, tickers: List[str], 
                    condition_field: str, condition_operator: str, condition_value: Union[float, str, int],
                    threshold_type: str = "absolute", enabled: bool = True, priority: str = "medium",
                    delivery_methods: Optional[List[str]] = None, frequency: str = "realtime", cooldown_minutes: int = 5):
    """
    Create a new alert rule
    """
    return alert_config_model.create_alert_rule(
        name, description, alert_type, tickers, condition_field, 
        condition_operator, condition_value, threshold_type, enabled, 
        priority, delivery_methods, frequency, cooldown_minutes
    )

def get_alert_rule(rule_id: str):
    """
    Get a specific alert rule
    """
    return alert_config_model.get_alert_rule(rule_id)

def get_all_alert_rules(ticker_filter: Optional[str] = None, type_filter: Optional[AlertType] = None, enabled_only: bool = True):
    """
    Get all alert rules with optional filters
    """
    return alert_config_model.get_all_alert_rules(ticker_filter, type_filter, enabled_only)

def update_alert_rule(rule_id: str, updates: Dict[str, Any]):
    """
    Update an existing alert rule
    """
    return alert_config_model.update_alert_rule(rule_id, updates)

def delete_alert_rule(rule_id: str):
    """
    Delete an alert rule
    """
    return alert_config_model.delete_alert_rule(rule_id)

def get_default_alert_rules():
    """
    Get default alert rules for new users
    """
    return alert_config_model.get_default_rules()