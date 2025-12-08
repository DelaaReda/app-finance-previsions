"""
User Preferences Service
Task: FC-API-033 - User Preferences Implementation
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from models.user_preferences import UserPreferencesModel
from storage.io import load_json, save_json
from services.cache_layer import load_or_compute


class UserPreferencesService:
    """
    Service for managing user preferences with robust error handling and caching
    """
    
    def __init__(self):
        self.model = UserPreferencesModel()
    
    def get_user_preferences(self, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Get user preferences with fallback to defaults if not available
        
        Args:
            user_id: User identifier
            
        Returns:
            User preferences dictionary
        """
        def compute_user_preferences():
            """Compute fresh preferences from storage"""
            try:
                return self.model.load_preferences(user_id)
            except Exception as e:
                print(f"Error loading preferences for {user_id}: {str(e)}")
                
                # Return default preferences to maintain never-empty contract
                return {
                    "theme": "dark",
                    "universe": ["SPY", "QQQ"],
                    "dashboard_layout": {
                        "columns": 2,
                        "show_news": True,
                        "show_macro": True,
                        "show_forecasts": True,
                        "order": ["news", "forecasts", "macro"]
                    },
                    "alerts": {
                        "enabled": True,
                        "thresholds": {
                            "volatility_high": 0.03,
                            "news_sentiment_extreme": 0.7,
                            "forecast_confidence_low": 0.6,
                            "price_change_alert": 0.05
                        },
                        "delivery": {
                            "email": True,
                            "push": True,
                            "frequency": "realtime"
                        }
                    },
                    "risk_tolerance": "moderate",
                    "preferred_metrics": [
                        "sharpe_ratio", "volatility", "beta", "alpha", "max_drawdown"
                    ],
                    "news_filters": {
                        "sentiment_threshold": 0.0,
                        "source_priority": ["bloomberg", "reuters", "wsj", "ft"],
                        "exclude_tickers": [],
                        "include_sector_news": True
                    },
                    "forecast_filters": {
                        "min_confidence": 0.5,
                        "horizons": ["1d", "1w", "1m"],
                        "min_return_threshold": 0.005
                    },
                    "data_refresh": {
                        "interval_minutes": 15,
                        "enable_auto_refresh": True,
                        "background_refresh": True
                    },
                    "privacy": {
                        "share_usage_data": True,
                        "enable_personalization": True
                    },
                    "custom_widgets": [],
                    "last_updated": datetime.utcnow().isoformat() + "Z",
                    "version": "1.0",
                    "error": str(e),
                    "message": f"Preferences loading failed for {user_id}, returning defaults to maintain never-empty contract"
                }
        
        # Use cache layer to serve latest available data, compute fresh if none available
        cache_key = f"user_prefs_{user_id}"
        pref_data = load_or_compute(
            key=cache_key,
            compute_fn=compute_user_preferences,
            source=["user_preferences_service", "preferences_load", "fc-api-033"]
        )
        
        return {
            "ok": True,
            "data": pref_data,
            "freshness": pref_data.get("last_updated", datetime.utcnow().isoformat() + "Z")
        }
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user preferences with validation and fallback protection
        
        Args:
            user_id: User identifier
            preferences: New preferences dictionary
            
        Returns:
            Status of the update operation
        """
        try:
            # Validate the preferences first
            validated_prefs = self.model._validate_preferences(preferences)
            
            # Save the validated preferences
            save_result = self.model.save_preferences(validated_prefs, user_id)
            
            if save_result:
                # Load and return the updated preferences
                updated_prefs = self.model.load_preferences(user_id)
                
                return {
                    "ok": True,
                    "data": {
                        "preferences": updated_prefs,
                        "user_id": user_id,
                        "updated_at": datetime.utcnow().isoformat() + "Z",
                        "changed_fields": self._get_changed_fields(updated_prefs, preferences),
                        "message": "Preferences updated successfully"
                    },
                    "freshness": updated_prefs.get("last_updated", datetime.utcnow().isoformat() + "Z")
                }
            else:
                # Save failed, return error but with fallback preferences
                fallback_prefs = self.model.load_preferences(user_id)  # Get current prefs
                return {
                    "ok": False,
                    "data": {
                        "preferences": fallback_prefs,
                        "user_id": user_id,
                        "updated_at": datetime.utcnow().isoformat() + "Z",
                        "error": "Preferences save failed",
                        "message": "Failed to save preferences but current preferences returned to maintain never-empty contract"
                    },
                    "freshness": "save_error"
                }
                
        except Exception as e:
            print(f"Error updating preferences for {user_id}: {str(e)}")
            
            # Return current preferences with error status to maintain never-empty contract
            current_prefs = self.model.load_preferences(user_id)
            return {
                "ok": False,
                "data": {
                    "preferences": current_prefs,
                    "user_id": user_id,
                    "updated_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e),
                    "message": f"Preferences update failed for {user_id}: {str(e)}, but fallback returned to maintain never-empty contract"
                },
                "freshness": "error"
            }
    
    def reset_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Reset user preferences to default values
        
        Args:
            user_id: User identifier
            
        Returns:
            Status of the reset operation
        """
        try:
            reset_result = self.model.reset_to_defaults(user_id)
            
            if reset_result:
                # Load the reset preferences
                reset_prefs = self.model.load_preferences(user_id)
                
                return {
                    "ok": True,
                    "data": {
                        "preferences": reset_prefs,
                        "user_id": user_id,
                        "reset_at": datetime.utcnow().isoformat() + "Z",
                        "message": "Preferences reset to default values successfully"
                    },
                    "freshness": reset_prefs.get("last_updated", datetime.utcnow().isoformat() + "Z")
                }
            else:
                # Reset failed, return current preferences with error
                current_prefs = self.model.load_preferences(user_id)
                return {
                    "ok": False,
                    "data": {
                        "preferences": current_prefs,
                        "user_id": user_id,
                        "reset_at": datetime.utcnow().isoformat() + "Z",
                        "error": "Reset operation failed",
                        "message": "Failed to reset preferences but current preferences returned to maintain never-empty contract"
                    },
                    "freshness": "reset_error"
                }
                
        except Exception as e:
            print(f"Error resetting preferences for {user_id}: {str(e)}")
            
            # Return current preferences with error status
            current_prefs = self.model.load_preferences(user_id)
            return {
                "ok": False,
                "data": {
                    "preferences": current_prefs,
                    "user_id": user_id,
                    "reset_at": None,
                    "error": str(e),
                    "message": f"Preferences reset failed for {user_id}: {str(e)}, but fallback returned to maintain never-empty contract"
                },
                "freshness": "error"
            }
    
    def _get_changed_fields(self, new_prefs: Dict[str, Any], old_prefs: Dict[str, Any]) -> List[str]:
        """
        Identify which fields changed during the update
        
        Args:
            new_prefs: New preferences after update
            old_prefs: Original preferences before update
            
        Returns:
            List of field names that changed
        """
        changed = []
        
        def flatten_dict(d, parent_key='', sep='.'):
            """Helper to flatten nested dictionaries"""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)
        
        flat_new = flatten_dict(new_prefs)
        flat_old = flatten_dict(old_prefs)
        
        for key, new_val in flat_new.items():
            old_val = flat_old.get(key)
            if old_val != new_val:
                changed.append(key)
        
        return changed


# Global instance
user_preferences_service = UserPreferencesService()


# Convenience functions
def get_user_prefs(user_id: str = "default_user"):
    """
    Get preferences for a user with structured response
    """
    return user_preferences_service.get_user_preferences(user_id)

def update_user_prefs(user_id: str, preferences: Dict[str, Any]):
    """
    Update user preferences with validation and response structure
    """
    return user_preferences_service.update_user_preferences(user_id, preferences)

def reset_user_prefs(user_id: str):
    """
    Reset user preferences to defaults with response structure
    """
    return user_preferences_service.reset_user_preferences(user_id)