"""
Alert Configuration Models
Task: FC-API-034 - Alert Rules Configuration
Author: ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AlertRule:
    """
    Represents a configured alert rule with parameters and triggers
    """
    id: str
    name: str
    rule_type: str  # 'rsi_oversold', 'rsi_overbought', 'news_sentiment', 'price_breakout', etc.
    enabled: bool
    parameters: Dict[str, Union[float, int, str, List[str]]]  # Specific parameters for each rule type
    threshold: float  # Threshold value for triggering the alert
    frequency: str  # 'realtime', 'minute', 'hour', 'day'
    assets: List[str]  # List of tickers this rule applies to
    priority: int  # Priority level (1-5, 5 being highest priority)
    created_at: str
    updated_at: str
    description: Optional[str] = None
    triggered_count: int = 0
    last_triggered: Optional[str] = None
    source: List[str] = None  # Track where the rule comes from
    
    def __post_init__(self):
        if self.source is None:
            self.source = ["user_config"]
    
    def dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rule_type': self.rule_type,
            'enabled': self.enabled,
            'parameters': self.parameters,
            'threshold': self.threshold,
            'frequency': self.frequency,
            'assets': self.assets,
            'priority': self.priority,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'description': self.description,
            'triggered_count': self.triggered_count,
            'last_triggered': self.last_triggered,
            'source': self.source
        }


@dataclass 
class AlertConfiguration:
    """
    Complete alert configuration containing multiple rules
    """
    rules: List[AlertRule]
    last_updated: str
    generated_at: str
    total_rules: int
    enabled_rules: int
    source: List[str]
    
    def dict(self):
        return {
            'rules': [rule.dict() for rule in self.rules],
            'last_updated': self.last_updated,
            'generated_at': self.generated_at,
            'total_rules': self.total_rules,
            'enabled_rules': self.enabled_rules,
            'source': self.source
        }


@dataclass
class AlertPayload:
    """
    Payload for triggering an alert
    """
    rule_id: str
    rule_name: str
    rule_type: str
    asset: str
    value: float
    threshold: float
    message: str
    timestamp: str
    source: List[str] = None
    
    def __post_init__(self):
        if self.source is None:
            self.source = ["alert_rule_trigger"]
    
    def dict(self):
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'rule_type': self.rule_type,
            'asset': self.asset,
            'value': self.value,
            'threshold': self.threshold,
            'message': self.message,
            'timestamp': self.timestamp,
            'source': self.source
        }