"""
Alert Rules Service
Task: FC-API-034 - Alert Rules Configuration
Author: ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add backend root to path for imports
backend_root = Path(__file__).resolve().parents[1]  # .../backend
for p in (backend_root,):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

try:
    from services.service_standard import utc_now_iso
except Exception:  # pragma: no cover
    from src.services.service_standard import utc_now_iso  # type: ignore


class AlertRulesService:
    """
    Service for managing alert rules configuration and state
    """
    
    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or "data/alerts/rules.json"
        self.alerts_dir = Path("data/alerts")
        self.alerts_dir.mkdir(exist_ok=True)
        # Initialize with default data if file doesn't exist
        rules_file = self.alerts_dir / "rules.json"
        if not rules_file.exists():
            default_data = self._create_default_rules()
            self.save_rules(default_data)
        
    def get_all_rules(self) -> Dict:
        """
        Load all configured alert rules from storage
        """
        try:
            rules_file = self.alerts_dir / "rules.json"
            if rules_file.exists():
                with open(rules_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        rules = data.get('rules', [])
                        
                        # Create configuration from rules (without converting back to objects for now, since we don't have the class properly defined)
                        enabled_count = sum(1 for rule in rules if rule.get('enabled', True))
                        
                        return {
                            "rules": rules,
                            "count": len(rules),
                            "enabled_count": enabled_count,
                            "last_updated": data.get("last_updated", utc_now_iso()),
                            "generated_at": utc_now_iso(),
                            "source": ["alert_rules_service", "persistent_storage", "fc-api-034"]
                        }
            # If file doesn't exist, create default rules
            default_rules = self._create_default_rules()
            self.save_rules(default_rules)
            return default_rules
        except Exception as e:
            print(f"Error loading alert rules: {str(e)}")
            # Return fallback data to maintain never-empty contract
            return {
                "rules": self._get_default_rules_list(),
                "count": 0,
                "enabled_count": 0,
                "last_updated": utc_now_iso(),
                "generated_at": utc_now_iso(),
                "source": ["alert_rules_service", "error_fallback", "fc-api-034"],
                "error": str(e),
                "message": "Failed to load alert rules but fallback returned to maintain never-empty contract"
            }
    
    def get_rule_by_id(self, rule_id: str) -> Optional[Dict]:
        """
        Get a specific rule by its ID
        """
        all_rules = self.get_all_rules()
        rules = all_rules.get('rules', [])
        
        for rule in rules:
            if rule.get('id') == rule_id:
                return rule
        
        return None
    
    def create_rule(self, rule_data: Dict) -> Dict:
        """
        Create a new alert rule with validation
        """
        try:
            # Validate rule parameters
            validated_rule = self._validate_rule_parameters(rule_data)
            
            # Load existing rules
            all_rules = self.get_all_rules()
            
            # Generate unique ID if not provided
            if not rule_data.get('id'):
                rule_data['id'] = f"rule_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Set timestamps
            rule_data["created_at"] = utc_now_iso()
            rule_data["updated_at"] = utc_now_iso()
            
            # Add to rules list
            existing_rules = all_rules.get('rules', [])
            existing_rules.append(rule_data)
            
            # Save updated rules
            updated_config = {
                "rules": existing_rules,
                "count": len(existing_rules),
                "enabled_count": sum(1 for r in existing_rules if r.get('enabled', True)),
                "last_updated": utc_now_iso(),
                "generated_at": utc_now_iso(),
                "source": ["alert_rules_service", "create_operation", "fc-api-034"]
            }
            
            self.save_rules(updated_config)
            
            return {
                "ok": True,
                "data": rule_data,
                "message": "Alert rule created successfully"
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "message": "Failed to create alert rule"
            }
    
    def update_rule(self, rule_id: str, rule_data: Dict) -> Dict:
        """
        Update an existing alert rule
        """
        try:
            # Load existing rules
            all_rules = self.get_all_rules()
            existing_rules = all_rules.get('rules', [])
            
            # Find the rule to update
            updated_rules = []
            found = False
            
            for rule in existing_rules:
                if rule.get('id') == rule_id:
                    # Update with new values but preserve some original fields
                    updated_rule = {**rule, **rule_data}
                    updated_rule["updated_at"] = utc_now_iso()
                    updated_rule['id'] = rule_id  # Ensure we don't change the ID
                    
                    validated_rule = self._validate_rule_parameters(updated_rule)
                    updated_rules.append(validated_rule)
                    found = True
                else:
                    updated_rules.append(rule)
            
            if not found:
                return {
                    "ok": False,
                    "error": "Rule not found",
                    "message": f"Alert rule with ID {rule_id} not found"
                }
            
            # Save updated rules
            updated_config = {
                "rules": updated_rules,
                "count": len(updated_rules),
                "enabled_count": sum(1 for r in updated_rules if r.get('enabled', True)),
                "last_updated": utc_now_iso(),
                "generated_at": utc_now_iso(),
                "source": ["alert_rules_service", "update_operation", "fc-api-034"]
            }
            
            self.save_rules(updated_config)
            
            return {
                "ok": True,
                "data": updated_config,
                "message": f"Alert rule {rule_id} updated successfully"
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "message": f"Failed to update alert rule {rule_id}"
            }
    
    def delete_rule(self, rule_id: str) -> Dict:
        """
        Delete an alert rule by ID
        """
        try:
            # Load existing rules
            all_rules = self.get_all_rules()
            existing_rules = all_rules.get('rules', [])
            
            # Filter out the rule to delete
            filtered_rules = [rule for rule in existing_rules if rule.get('id') != rule_id]
            
            if len(filtered_rules) == len(existing_rules):
                return {
                    "ok": False,
                    "error": "Rule not found",
                    "message": f"Alert rule with ID {rule_id} not found"
                }
            
            # Save updated rules
            updated_config = {
                "rules": filtered_rules,
                "count": len(filtered_rules),
                "enabled_count": sum(1 for r in filtered_rules if r.get('enabled', True)),
                "last_updated": utc_now_iso(),
                "generated_at": utc_now_iso(),
                "source": ["alert_rules_service", "delete_operation", "fc-api-034"]
            }
            
            self.save_rules(updated_config)
            
            return {
                "ok": True,
                "data": updated_config,
                "message": f"Alert rule {rule_id} deleted successfully"
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "message": f"Failed to delete alert rule {rule_id}"
            }
    
    def save_rules(self, rules_config: Dict):
        """
        Save rules configuration to persistent storage
        """
        try:
            # Ensure directory exists
            self.alerts_dir.mkdir(exist_ok=True)
            
            # Write to file
            rules_file = self.alerts_dir / "rules.json"
            with open(rules_file, 'w', encoding='utf-8') as f:
                json.dump(rules_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving alert rules: {str(e)}")
    
    def _validate_rule_parameters(self, rule_data: Dict) -> Dict:
        """
        Validate alert rule parameters to ensure they're within acceptable ranges
        """
        rule_type = rule_data.get('rule_type', '').lower()
        params = rule_data.get('parameters', {})
        threshold = rule_data.get('threshold', 0.0)
        
        # Validate threshold based on rule type
        if rule_type in ['rsi_oversold', 'rsi_overbought']:
            # RSI values are typically 0-100
            if not 0 <= threshold <= 100:
                raise ValueError(f"RSI threshold must be between 0 and 100, got {threshold}")
        
        elif rule_type == 'news_sentiment':
            # News sentiment typically is -1 to 1 (maybe 0-100 scale)
            if not -1 <= threshold <= 1:
                # Allow 0-100 scale as well
                if not 0 <= threshold <= 100:
                    raise ValueError(f"News sentiment threshold must be between -1 and 1 (or 0-100), got {threshold}")
        
        elif rule_type == 'price_breakout':
            # Price breakout thresholds (as percentage changes)
            if not -100 <= threshold <= 100:
                raise ValueError(f"Price breakout threshold must be between -100 and 100, got {threshold}")
        
        # Validate other parameters
        frequency = rule_data.get('frequency', 'realtime').lower()
        allowed_frequencies = ['realtime', 'minute', 'hour', 'day', 'week']
        if frequency not in allowed_frequencies:
            rule_data['frequency'] = 'realtime'  # Default to realtime if invalid
        
        # Validate priority
        priority = rule_data.get('priority', 3)
        if not isinstance(priority, int) or not 1 <= priority <= 5:
            rule_data['priority'] = 3  # Default to medium priority
        
        # Ensure assets is a list
        assets = rule_data.get('assets', ['SPY', 'QQQ'])
        if isinstance(assets, str):
            assets = [assets]
        elif not isinstance(assets, list):
            assets = ['SPY', 'QQQ']  # Default assets
        rule_data['assets'] = assets
        
        # Validate that rule_type is valid
        allowed_types = [
            'rsi_oversold', 'rsi_overbought', 'news_sentiment', 
            'price_breakout', 'volume_spike', 'volatility_spike',
            'macd_crossover', 'sma_cross', 'bollinger_breakout'
        ]
        if rule_type not in allowed_types:
            raise ValueError(f"Invalid rule type: {rule_type}. Allowed types: {allowed_types}")
        
        return rule_data
    
    def _create_default_rules(self):
        """
        Create default alert rules if none exist
        """
        default_rules = [
            {
                "id": "default_rsi_oversold",
                "name": "RSI Oversold (30)",
                "rule_type": "rsi_oversold",
                "enabled": True,
                "parameters": {
                    "rsi_period": 14,
                    "oversold_level": 30
                },
                "threshold": 30.0,
                "frequency": "minute",
                "assets": ["SPY", "QQQ", "AAPL", "NVDA", "MSFT"],
                "priority": 4,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "description": "Alert when RSI drops below 30 (oversold condition)",
                "triggered_count": 0,
                "last_triggered": None
            },
            {
                "id": "default_news_negative",
                "name": "Negative News Sentiment",
                "rule_type": "news_sentiment",
                "enabled": True,
                "parameters": {
                    "sentiment_threshold": -0.5,
                    "asset_specific": True
                },
                "threshold": -0.5,
                "frequency": "hour",
                "assets": ["SPY", "QQQ", "AAPL", "NVDA", "MSFT"],
                "priority": 3,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "description": "Alert on negative news sentiment below threshold",
                "triggered_count": 0,
                "last_triggered": None
            }
        ]
        
        config = {
            "rules": default_rules,
            "count": len(default_rules),
            "enabled_count": sum(1 for r in default_rules if r.get('enabled', True)),
            "last_updated": utc_now_iso(),
            "generated_at": utc_now_iso(),
            "source": ["alert_rules_service", "defaults", "fc-api-034"]
        }
        
        return config
    
    def _get_default_rules_list(self):
        """
        Return default rules list to maintain never-empty contract
        """
        return [
            {
                "id": "fallback_rule",
                "name": "Default Alert Rule",
                "rule_type": "rsi_oversold",
                "enabled": True,
                "parameters": {"level": 30},
                "threshold": 30.0,
                "frequency": "realtime",
                "assets": ["SPY", "QQQ"],
                "priority": 3,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "description": "Fallback rule to maintain never-empty contract",
                "triggered_count": 0,
                "last_triggered": None,
                "source": ["alert_rules_service", "fallback", "fc-api-034"]
            }
        ]


# Global instance
alert_rules_service = AlertRulesService()
