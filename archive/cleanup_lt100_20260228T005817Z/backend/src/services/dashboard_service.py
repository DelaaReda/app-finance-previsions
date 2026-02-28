"""
Dashboard Service
Service pour exposer les KPIs du dashboard
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
"""
from typing import Dict, Any
from pathlib import Path
import sys
import logging

# Add backend to path
backend_root = Path(__file__).resolve().parents[3]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

logger = logging.getLogger(__name__)

try:
    from services.service_standard import utc_now_iso, unwrap_storage_payload
except Exception:  # pragma: no cover
    from src.services.service_standard import utc_now_iso, unwrap_storage_payload  # type: ignore

try:
    from backend.storage.io import load_json
except ImportError:
    try:
        from backend.storage.base import load_json
    except ImportError:
        logger.warning("storage modules not available")
        def load_json(key):
            data_dir = Path(__file__).resolve().parents[3] / "data" / "dashboard"
            filepath = data_dir / f"{key}.json"
            if not filepath.exists():
                return None
            import json
            return json.loads(filepath.read_text())


def get_dashboard_kpis() -> Dict[str, Any]:
    """
    Récupère les KPIs du dashboard depuis le stockage
    
    Returns:
        Dict avec les KPIs ou structure vide si pas de données
    """
    try:
        # Charger depuis le stockage
        kpis_data = unwrap_storage_payload(load_json("dashboard/kpis"))
        if kpis_data:
            return kpis_data
        
        # Fallback: structure vide mais valide
        logger.warning("No dashboard KPIs found, returning empty structure")
        return {
            "forecasts": {
                "total": 0,
                "high_confidence": 0,
                "avg_confidence": 0,
                "bullish": 0,
                "bearish": 0,
            },
            "backtests": {
                "hit_rate": 0,
                "sharpe_ratio": 0,
                "status": "pending",
            },
            "news": {
                "recent_count": 0,
                "avg_score": 0,
            },
            "system": {
                "last_forecast_update": None,
                "last_news_update": None,
                "last_backtest_update": None,
            },
            "generated_at": utc_now_iso(),
        }
        
    except Exception as e:
        logger.error(f"Error loading dashboard KPIs: {str(e)}")
        # Retourner structure vide mais valide
        return {
            "forecasts": {"total": 0, "high_confidence": 0, "avg_confidence": 0, "bullish": 0, "bearish": 0},
            "backtests": {"hit_rate": 0, "sharpe_ratio": 0, "status": "pending"},
            "news": {"recent_count": 0, "avg_score": 0},
            "system": {"last_forecast_update": None, "last_news_update": None, "last_backtest_update": None},
            "generated_at": utc_now_iso(),
        }
