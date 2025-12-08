"""
Alerts Service - Manage user alerts
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: API-ALERTS-001 - Alerts CRUD operations
"""
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Alert types
AlertType = Literal[
    "price",           # Price threshold (e.g., AAPL > $180)
    "sentiment",       # Sentiment shift (e.g., news sentiment < -0.5)
    "forecast",        # Forecast change (e.g., confidence < 0.7)
    "correlation",     # Correlation break (e.g., AAPL-MSFT < 0.5)
    "regime",          # Market regime change (e.g., regime = HIGH_VOLATILITY)
    "volume",          # Volume spike (e.g., volume > 2x avg)
    "volatility",      # Volatility threshold (e.g., volatility > 0.3)
    "technical"        # Technical indicator (e.g., RSI < 30)
]

# Alert status
AlertStatus = Literal["active", "triggered", "snoozed", "disabled"]


class AlertCondition(BaseModel):
    """Alert condition definition"""
    field: str = Field(..., description="Field to monitor (e.g., 'price', 'sentiment', 'rsi')")
    operator: Literal[">", "<", ">=", "<=", "==", "!="] = Field(..., description="Comparison operator")
    value: float = Field(..., description="Threshold value")
    
    def evaluate(self, current_value: float) -> bool:
        """Evaluate if condition is met"""
        if self.operator == ">":
            return current_value > self.value
        elif self.operator == "<":
            return current_value < self.value
        elif self.operator == ">=":
            return current_value >= self.value
        elif self.operator == "<=":
            return current_value <= self.value
        elif self.operator == "==":
            return current_value == self.value
        elif self.operator == "!=":
            return current_value != self.value
        return False


class Alert(BaseModel):
    """Alert model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = Field(..., description="Ticker symbol")
    type: AlertType = Field(..., description="Alert type")
    condition: AlertCondition = Field(..., description="Alert condition")
    message: str = Field(..., description="Alert message/description")
    status: AlertStatus = Field(default="active", description="Alert status")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    triggered_at: Optional[str] = Field(None, description="Last trigger timestamp")
    triggered_count: int = Field(default=0, description="Number of times triggered")
    snoozed_until: Optional[str] = Field(None, description="Snoozed until timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AlertsService:
    """Service for managing user alerts"""
    
    def __init__(self, storage_path: str = "data/user_alerts.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_alerts()
    
    def _load_alerts(self) -> None:
        """Load alerts from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.alerts = {
                        alert_id: Alert(**alert_data)
                        for alert_id, alert_data in data.items()
                    }
                logger.info(f"Loaded {len(self.alerts)} alerts from storage")
            except Exception as e:
                logger.error(f"Error loading alerts: {str(e)}")
                self.alerts = {}
        else:
            self.alerts = {}
            logger.info("No existing alerts found, starting fresh")
    
    def _save_alerts(self) -> None:
        """Save alerts to storage"""
        try:
            data = {
                alert_id: alert.model_dump()
                for alert_id, alert in self.alerts.items()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.alerts)} alerts to storage")
        except Exception as e:
            logger.error(f"Error saving alerts: {str(e)}")
    
    def create_alert(
        self,
        ticker: str,
        type: AlertType,
        condition: AlertCondition,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Create a new alert
        
        Args:
            ticker: Ticker symbol
            type: Alert type
            condition: Alert condition
            message: Alert message
            metadata: Optional metadata
        
        Returns:
            Created alert
        """
        alert = Alert(
            ticker=ticker.upper(),
            type=type,
            condition=condition,
            message=message,
            metadata=metadata or {}
        )
        
        self.alerts[alert.id] = alert
        self._save_alerts()
        
        logger.info(f"Created alert {alert.id} for {ticker} ({type})")
        return alert
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        return self.alerts.get(alert_id)
    
    def list_alerts(
        self,
        ticker: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        type: Optional[AlertType] = None
    ) -> List[Alert]:
        """
        List alerts with optional filters
        
        Args:
            ticker: Filter by ticker
            status: Filter by status
            type: Filter by type
        
        Returns:
            List of alerts
        """
        alerts = list(self.alerts.values())
        
        # Apply filters
        if ticker:
            alerts = [a for a in alerts if a.ticker == ticker.upper()]
        if status:
            alerts = [a for a in alerts if a.status == status]
        if type:
            alerts = [a for a in alerts if a.type == type]
        
        # Sort by created_at (newest first)
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        
        return alerts
    
    def update_alert(
        self,
        alert_id: str,
        condition: Optional[AlertCondition] = None,
        message: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Alert]:
        """
        Update an alert
        
        Args:
            alert_id: Alert ID
            condition: New condition (optional)
            message: New message (optional)
            status: New status (optional)
            metadata: New metadata (optional)
        
        Returns:
            Updated alert or None if not found
        """
        alert = self.alerts.get(alert_id)
        if not alert:
            return None
        
        # Update fields
        if condition:
            alert.condition = condition
        if message:
            alert.message = message
        if status:
            alert.status = status
        if metadata:
            alert.metadata = metadata
        
        alert.updated_at = datetime.now(timezone.utc).isoformat()
        
        self._save_alerts()
        logger.info(f"Updated alert {alert_id}")
        
        return alert
    
    def delete_alert(self, alert_id: str) -> bool:
        """
        Delete an alert
        
        Args:
            alert_id: Alert ID
        
        Returns:
            True if deleted, False if not found
        """
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            self._save_alerts()
            logger.info(f"Deleted alert {alert_id}")
            return True
        return False
    
    def trigger_alert(self, alert_id: str, current_value: float) -> bool:
        """
        Mark alert as triggered
        
        Args:
            alert_id: Alert ID
            current_value: Current value that triggered the alert
        
        Returns:
            True if triggered, False otherwise
        """
        alert = self.alerts.get(alert_id)
        if not alert or alert.status != "active":
            return False
        
        # Check if snoozed
        if alert.snoozed_until:
            snooze_time = datetime.fromisoformat(alert.snoozed_until.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) < snooze_time:
                logger.debug(f"Alert {alert_id} is snoozed until {alert.snoozed_until}")
                return False
        
        # Update alert
        alert.status = "triggered"
        alert.triggered_at = datetime.now(timezone.utc).isoformat()
        alert.triggered_count += 1
        alert.metadata["last_trigger_value"] = current_value
        alert.updated_at = datetime.now(timezone.utc).isoformat()
        
        self._save_alerts()
        logger.info(f"Alert {alert_id} triggered with value {current_value}")
        
        return True
    
    def snooze_alert(self, alert_id: str, duration_minutes: int = 60) -> Optional[Alert]:
        """
        Snooze an alert for specified duration
        
        Args:
            alert_id: Alert ID
            duration_minutes: Snooze duration in minutes
        
        Returns:
            Updated alert or None if not found
        """
        alert = self.alerts.get(alert_id)
        if not alert:
            return None
        
        from datetime import timedelta
        snooze_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        
        alert.status = "snoozed"
        alert.snoozed_until = snooze_until.isoformat()
        alert.updated_at = datetime.now(timezone.utc).isoformat()
        
        self._save_alerts()
        logger.info(f"Snoozed alert {alert_id} until {snooze_until}")
        
        return alert
    
    def test_alert(self, alert_id: str, test_value: float) -> Dict[str, Any]:
        """
        Test if alert condition would be met with given value
        
        Args:
            alert_id: Alert ID
            test_value: Test value
        
        Returns:
            Test result
        """
        alert = self.alerts.get(alert_id)
        if not alert:
            return {"error": "Alert not found"}
        
        would_trigger = alert.condition.evaluate(test_value)
        
        return {
            "alert_id": alert_id,
            "ticker": alert.ticker,
            "condition": {
                "field": alert.condition.field,
                "operator": alert.condition.operator,
                "threshold": alert.condition.value
            },
            "test_value": test_value,
            "would_trigger": would_trigger,
            "message": alert.message if would_trigger else "Condition not met"
        }
    
    def get_triggered_alerts(self, limit: int = 50) -> List[Alert]:
        """
        Get recently triggered alerts
        
        Args:
            limit: Maximum number of alerts to return
        
        Returns:
            List of triggered alerts
        """
        triggered = [a for a in self.alerts.values() if a.status == "triggered"]
        triggered.sort(key=lambda a: a.triggered_at or "", reverse=True)
        return triggered[:limit]


# Singleton instance
_alerts_service: Optional[AlertsService] = None


def get_alerts_service() -> AlertsService:
    """Get or create alerts service singleton"""
    global _alerts_service
    if _alerts_service is None:
        _alerts_service = AlertsService()
    return _alerts_service
