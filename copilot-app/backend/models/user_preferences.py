"""
User Preferences Model
Task: FC-API-033 - User Preferences
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
import json
import sys
from pathlib import Path

# Add backend root to path for imports
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from storage.io import load_json, save_json


class UserPreferencesModel:
    """
    Model for managing user preferences including theme, universe, thresholds, etc.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.preferences_file = backend_root / "data" / "users" / f"preferences_{user_id}.json"
        self.preferences_dir = self.preferences_file.parent
        self.preferences_dir.mkdir(parents=True, exist_ok=True)
    
    def get_default_preferences(self) -> Dict[str, Any]:
        """
        Get default preferences structure
        """
        return {
            "theme": "dark",  # dark, light, auto
            "universe": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"],  # Default tickers to track
            "dashboard_layout": {
                "columns": 2,  # Number of columns in dashboard
                "show_news": True,
                "show_macro": True,
                "show_forecasts": True,
                "order": ["news", "forecasts", "macro"]  # Order of dashboard sections
            },
            "alerts": {
                "enabled": True,
                "thresholds": {
                    "volatility_high": 0.03,  # Alert when volatility exceeds 3%
                    "news_sentiment_extreme": 0.7,  # Alert when sentiment is >0.7 or <-0.7
                    "forecast_confidence_low": 0.6,  # Alert when forecast confidence drops below 60%
                    "price_change_alert": 0.05  # Alert on price change >5%
                },
                "delivery": {
                    "email": True,
                    "push": True,
                    "frequency": "realtime"  # realtime, hourly, daily, weekly
                }
            },
            "risk_tolerance": "moderate",  # conservative, moderate, aggressive
            "preferred_metrics": [
                "sharpe_ratio", "volatility", "beta", "alpha", "max_drawdown"
            ],
            "news_filters": {
                "sentiment_threshold": 0.0,  # Show news with sentiment > threshold
                "source_priority": ["bloomberg", "reuters", "wsj", "ft"],  # Priority sources
                "exclude_tickers": [],  # Tickers to exclude from news feed
                "include_sector_news": True
            },
            "forecast_filters": {
                "min_confidence": 0.5,  # Show forecasts with at least 50% confidence
                "horizons": ["1d", "1w", "1m"],  # Default forecast horizons to show
                "min_return_threshold": 0.005  # Minimum expected return to show (0.5%)
            },
            "data_refresh": {
                "interval_minutes": 15,  # How frequently to refresh data
                "enable_auto_refresh": True,
                "background_refresh": True  # Whether to refresh in background
            },
            "privacy": {
                "share_usage_data": True,
                "enable_personalization": True
            },
            "custom_widgets": [],  # List of custom widget IDs if any
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "version": "1.0"
        }
    
    def load_preferences(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Load user preferences from storage
        
        Args:
            user_id: Optional user ID (uses instance user_id if not provided)
        
        Returns:
            User preferences or default preferences if not found
        """
        target_user_id = user_id or self.user_id
        pref_file = backend_root / "data" / "users" / f"preferences_{target_user_id}.json"
        
        try:
            # Try to load from storage
            prefs_data = load_json(f"users/preferences_{target_user_id}")
            
            if prefs_data and isinstance(prefs_data, dict):
                # Merge with defaults to ensure all fields exist
                defaults = self.get_default_preferences()
                user_prefs = self._deep_merge(defaults, prefs_data)
                
                # Ensure required fields are present
                user_prefs["last_updated"] = datetime.utcnow().isoformat() + "Z"
                
                return user_prefs
            else:
                # No preferences found, return defaults
                defaults = self.get_default_preferences()
                defaults["last_updated"] = datetime.utcnow().isoformat() + "Z"
                return defaults
                
        except Exception as e:
            print(f"Error loading preferences for {target_user_id}: {str(e)}")
            
            # Return default preferences to maintain never-empty contract
            defaults = self.get_default_preferences()
            defaults["last_updated"] = datetime.utcnow().isoformat() + "Z"
            defaults["message"] = f"Preferences loading failed: {str(e)}, using defaults to maintain never-empty contract"
            
            return defaults
    
    def save_preferences(self, preferences: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        """
        Save user preferences to storage
        
        Args:
            preferences: Dictionary of user preferences
            user_id: Optional user ID (uses instance user_id if not provided)
        
        Returns:
            True if successful, False otherwise
        """
        target_user_id = user_id or self.user_id
        
        try:
            # Validate preferences structure
            validated_prefs = self._validate_preferences(preferences)
            
            # Add metadata
            validated_prefs["last_updated"] = datetime.utcnow().isoformat() + "Z"
            validated_prefs["user_id"] = target_user_id
            validated_prefs["version"] = "1.0"
            validated_prefs["source"] = ["user_preferences_model", "save_operation", "fc-api-033"]
            
            # Save to storage
            save_success = save_json(f"users/preferences_{target_user_id}", validated_prefs, 
                                   source=["user_preferences", "user_save", "fc-api-033"])
            
            if save_success:
                print(f"Successfully saved preferences for {target_user_id}")
                return True
            else:
                print(f"Failed to save preferences for {target_user_id}")
                return False
                
        except Exception as e:
            print(f"Error saving preferences for {target_user_id}: {str(e)}")
            
            # Try to save with minimal structure to maintain never-empty contract
            fallback_prefs = {
                "theme": "dark",
                "universe": ["SPY", "QQQ"],
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "user_id": target_user_id,
                "version": "1.0",
                "error": str(e),
                "message": "Preferences save failed but minimal fallback saved to maintain never-empty contract",
                "source": ["user_preferences_model", "save_error_fallback", "fc-api-033"]
            }
            
            try:
                save_json(f"users/preferences_{target_user_id}", fallback_prefs,
                         source=["user_preferences", "fallback_save", "fc-api-033"])
                return False  # Return False as main save failed, but fallback was saved
            except:
                return False  # Both main and fallback saves failed
    
    def _validate_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize user preferences
        
        Args:
            preferences: Raw preferences dictionary
            
        Returns:
            Validated and normalized preferences
        """
        validated = dict(preferences)
        
        # Validate theme
        if "theme" in validated:
            valid_themes = ["dark", "light", "auto"]
            if validated["theme"] not in valid_themes:
                validated["theme"] = "dark"  # Default to dark
        
        # Validate universe
        if "universe" in validated:
            if not isinstance(validated["universe"], list):
                validated["universe"] = ["SPY", "QQQ"]  # Default if invalid
            else:
                # Validate tickers (basic format check)
                valid_tickers = []
                for ticker in validated["universe"]:
                    if isinstance(ticker, str) and 1 <= len(ticker) <= 10 and ticker.isalnum():
                        valid_tickers.append(ticker.upper())
                validated["universe"] = valid_tickers or ["SPY", "QQQ"]
        
        # Validate dashboard layout
        if "dashboard_layout" in validated:
            if not isinstance(validated["dashboard_layout"], dict):
                validated["dashboard_layout"] = self.get_default_preferences()["dashboard_layout"]
            else:
                layout = validated["dashboard_layout"]
                layout["columns"] = max(1, min(4, layout.get("columns", 2)))  # Between 1-4 columns
                layout["show_news"] = bool(layout.get("show_news", True))
                layout["show_macro"] = bool(layout.get("show_macro", True))
                layout["show_forecasts"] = bool(layout.get("show_forecasts", True))
        
        # Validate alerts settings
        if "alerts" in validated:
            if not isinstance(validated["alerts"], dict):
                validated["alerts"] = self.get_default_preferences()["alerts"]
            else:
                alerts = validated["alerts"]
                alerts["enabled"] = bool(alerts.get("enabled", True))
                
                if "thresholds" in alerts and isinstance(alerts["thresholds"], dict):
                    thresholds = alerts["thresholds"]
                    # Validate numeric thresholds
                    for key in ["volatility_high", "news_sentiment_extreme", "forecast_confidence_low", "price_change_alert"]:
                        if key in thresholds:
                            val = thresholds[key]
                            if not isinstance(val, (int, float)) or val < 0 or val > 5:  # Reasonable range
                                thresholds[key] = self.get_default_preferences()["alerts"]["thresholds"][key]
        
        # Validate risk tolerance
        if "risk_tolerance" in validated:
            valid_risk_levels = ["conservative", "moderate", "aggressive"]
            if validated["risk_tolerance"] not in valid_risk_levels:
                validated["risk_tolerance"] = "moderate"
        
        # Validate data refresh settings
        if "data_refresh" in validated:
            if not isinstance(validated["data_refresh"], dict):
                validated["data_refresh"] = self.get_default_preferences()["data_refresh"]
            else:
                refresh = validated["data_refresh"]
                refresh["interval_minutes"] = max(1, min(1440, refresh.get("interval_minutes", 15)))  # 1 min to 24 hrs
                refresh["enable_auto_refresh"] = bool(refresh.get("enable_auto_refresh", True))
                refresh["background_refresh"] = bool(refresh.get("background_refresh", True))
        
        # Add default last_updated if not present
        if "last_updated" not in validated:
            validated["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        return validated
    
    def _deep_merge(self, default: Dict, override: Dict) -> Dict[str, Any]:
        """
        Deep merge two dictionaries, with override values taking precedence
        
        Args:
            default: Default values dictionary
            override: Override values dictionary
            
        Returns:
            Merged dictionary
        """
        result = dict(default)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override with new value
                result[key] = value
        
        return result
    
    def update_preference(self, key_path: str, value: Any, user_id: Optional[str] = None) -> bool:
        """
        Update a specific preference by key path (dot notation)
        
        Args:
            key_path: Path to preference (e.g. "alerts.enabled" or "theme")
            value: New value for the preference
            user_id: Optional user ID (uses instance user_id if not provided)
        
        Returns:
            True if successful, False otherwise
        """
        target_user_id = user_id or self.user_id
        
        try:
            current_prefs = self.load_preferences(target_user_id)
            
            # Navigate to the target location in the preferences
            keys = key_path.split('.')
            current_dict = current_prefs
            for k in keys[:-1]:
                if not isinstance(current_dict.get(k), dict):
                    current_dict[k] = {}
                current_dict = current_dict[k]
            
            # Update the final key
            current_dict[keys[-1]] = value
            
            # Validate the updated preferences
            validated_prefs = self._validate_preferences(current_prefs)
            
            # Save the updated preferences
            return self.save_preferences(validated_prefs, target_user_id)
            
        except Exception as e:
            print(f"Error updating preference {key_path} for {target_user_id}: {str(e)}")
            return False
    
    def reset_to_defaults(self, user_id: Optional[str] = None) -> bool:
        """
        Reset user preferences to defaults
        
        Args:
            user_id: Optional user ID (uses instance user_id if not provided)
        
        Returns:
            True if successful, False otherwise
        """
        target_user_id = user_id or self.user_id
        
        try:
            defaults = self.get_default_preferences()
            defaults["last_updated"] = datetime.utcnow().isoformat() + "Z"
            defaults["reset"] = True
            defaults["message"] = "Preferences reset to default values"
            
            return self.save_preferences(defaults, target_user_id)
            
        except Exception as e:
            print(f"Error resetting preferences for {target_user_id}: {str(e)}")
            return False


# Global instance for default user
user_prefs_model = UserPreferencesModel()


# Convenience functions
def get_user_preferences(user_id: str = "default_user") -> Dict[str, Any]:
    """
    Get user preferences for the specified user
    """
    model = UserPreferencesModel(user_id)
    return model.load_preferences(user_id)


def save_user_preferences(user_id: str, preferences: Dict[str, Any]) -> bool:
    """
    Save user preferences for the specified user
    """
    model = UserPreferencesModel(user_id)
    return model.save_preferences(preferences, user_id)


def update_user_preference(user_id: str, key_path: str, value: Any) -> bool:
    """
    Update a specific user preference
    """
    model = UserPreferencesModel(user_id)
    return model.update_preference(key_path, value, user_id)


def reset_user_preferences(user_id: str) -> bool:
    """
    Reset user preferences to defaults
    """
    model = UserPreferencesModel(user_id)
    return model.reset_to_defaults(user_id)