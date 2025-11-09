"""
Dashboard KPIs Refresh Job
Génère les métriques KPIs pour le dashboard principal
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Créer pipeline pour MetricCard / StatsGrid
"""
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

logger = logging.getLogger(__name__)

try:
    from storage.io import save_json, load_json
except ImportError:
    logger.warning("storage.io not available, using fallback")
    def save_json(key, payload, source=None, version="v1"):
        # Handle nested paths (e.g., "dashboard/kpis" -> data/dashboard/kpis.json)
        data_dir = Path(__file__).parent.parent / "data"
        filepath = data_dir / f"{key}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        import json
        final_payload = dict(payload)
        final_payload["freshness"] = datetime.utcnow().isoformat() + "Z"
        final_payload["source"] = source or []
        final_payload["version"] = version
        filepath.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2))
    
    def load_json(key):
        data_dir = Path(__file__).parent.parent / "data"
        filepath = data_dir / f"{key}.json"
        if not filepath.exists():
            return None
        import json
        return json.loads(filepath.read_text())


def calculate_dashboard_kpis() -> Dict[str, Any]:
    """
    Calcule les KPIs du dashboard en agrégeant les données disponibles
    Inclut maintenant top_signals et top_risks depuis brief_weekly
    """
    logger.info("Calculating dashboard KPIs...")
    
    # Charger les données disponibles
    forecasts_data = load_json("forecasts") or {}
    news_data = load_json("news_feed") or {}
    backtests_data = load_json("backtests") or {}
    brief_data = load_json("brief_weekly") or {}
    
    # Extraire les données
    forecasts = forecasts_data.get("data", {}).get("rows", []) or forecasts_data.get("rows", [])
    news_articles = news_data.get("data", {}).get("articles", []) or news_data.get("articles", [])
    backtest_results = backtests_data.get("data", {}).get("results", {}) or backtests_data.get("results", {})
    
    # Calculer les KPIs basiques
    total_forecasts = len(forecasts)
    high_confidence_forecasts = len([f for f in forecasts if f.get("confidence", 0) >= 0.7])
    avg_confidence = sum(f.get("confidence", 0) for f in forecasts) / total_forecasts if total_forecasts > 0 else 0
    
    # KPIs basés sur les prévisions
    bullish_count = len([f for f in forecasts if f.get("direction") == "up"])
    bearish_count = len([f for f in forecasts if f.get("direction") == "down"])
    
    # Count unique tickers and horizons
    tickers_set = set()
    horizons_set = set()
    for f in forecasts:
        if f.get("ticker"):
            tickers_set.add(f["ticker"])
        if f.get("horizon"):
            horizons_set.add(f["horizon"])
    
    # KPIs basés sur les backtests
    hit_rate = backtest_results.get("hit_rate", 0) * 100 if isinstance(backtest_results.get("hit_rate"), (int, float)) else 0
    sharpe_ratio = backtest_results.get("sharpe_ratio", 0) if isinstance(backtest_results.get("sharpe_ratio"), (int, float)) else 0
    
    # KPIs basés sur les news
    recent_news_count = len(news_articles)
    avg_news_score = sum(a.get("score", 0) for a in news_articles) / recent_news_count if recent_news_count > 0 else 0
    
    # Extraire top_signals et top_risks depuis brief
    top_signals = []
    top_risks = []
    
    if brief_data and "data" in brief_data:
        brief_weekly = brief_data["data"].get("weekly", {})
        top_signals = brief_weekly.get("top_signals", [])[:3] or brief_data["data"].get("top_signals", [])[:3]
        top_risks = brief_weekly.get("top_risks", [])[:3] or brief_data["data"].get("top_risks", [])[:3]
    
    # Fallback: générer depuis forecasts si brief vide
    if not top_signals and not top_risks and forecasts:
        # Top signals: bullish forecasts avec haute confiance
        bullish_forecasts = [
            f for f in forecasts 
            if f.get("direction") == "up" and f.get("confidence", 0) > 0.5
        ]
        bullish_forecasts.sort(
            key=lambda x: x.get("confidence", 0) * abs(x.get("expected_return", 0)),
            reverse=True
        )
        
        for f in bullish_forecasts[:3]:
            top_signals.append({
                "ticker": f.get("ticker"),
                "direction": "up",
                "confidence": f.get("confidence", 0),
                "expected_return": f.get("expected_return", 0),
                "horizon": f.get("horizon", "1m"),
                "reason": f.get("explanation", "Bullish forecast"),
            })
        
        # Top risks: bearish forecasts ou faible confiance
        bearish_forecasts = [
            f for f in forecasts 
            if f.get("direction") == "down" or f.get("confidence", 0) < 0.3
        ]
        bearish_forecasts.sort(
            key=lambda x: (1 - x.get("confidence", 0)) * abs(x.get("expected_return", 0)),
            reverse=True
        )
        
        for f in bearish_forecasts[:3]:
            top_risks.append({
                "ticker": f.get("ticker"),
                "direction": "down",
                "confidence": f.get("confidence", 0),
                "expected_return": f.get("expected_return", 0),
                "horizon": f.get("horizon", "1m"),
                "reason": f.get("explanation", "Bearish forecast"),
            })
    
    kpis = {
        # KPIs basiques
        "last_forecast_dt": forecasts_data.get("last_update") or forecasts_data.get("freshness"),
        "total_forecasts": total_forecasts,
        "tickers_tracked": len(tickers_set),
        "available_horizons": sorted(list(horizons_set)),
        
        # Top signaux et risques (NOUVEAU)
        "top_signals": top_signals,
        "top_risks": top_risks,
        
        # Structure legacy (pour compatibilité)
        "forecasts": {
            "total": total_forecasts,
            "high_confidence": high_confidence_forecasts,
            "avg_confidence": round(avg_confidence * 100, 1),
            "bullish": bullish_count,
            "bearish": bearish_count,
        },
        "backtests": {
            "hit_rate": round(hit_rate, 1),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "status": "active" if backtest_results else "pending",
        },
        "news": {
            "recent_count": recent_news_count,
            "avg_score": round(avg_news_score, 2),
        },
        "system": {
            "last_forecast_update": forecasts_data.get("last_update") or forecasts_data.get("freshness"),
            "last_news_update": news_data.get("last_update") or news_data.get("freshness"),
            "last_backtest_update": backtests_data.get("last_update") or backtests_data.get("freshness"),
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    
    logger.info(f"✅ Calculated {len(kpis)} KPI categories with {len(top_signals)} signals and {len(top_risks)} risks")
    return kpis


def run_dashboard_refresh_job(force: bool = False) -> Dict[str, Any]:
    """
    Job principal pour rafraîchir les KPIs du dashboard
    
    Args:
        force: Si True, force le recalcul même si les données sont récentes
    
    Returns:
        Résultat du job avec statistiques
    """
    logger.info("Starting dashboard KPIs refresh job...")
    
    try:
        # Calculer les KPIs
        kpis = calculate_dashboard_kpis()
        
        # Sauvegarder
        save_json("dashboard/kpis", kpis, source=["job:dashboard_refresh", "aggregated_data"], version="v1")
        
        result = {
            "status": "completed",
            "kpis_generated": len(kpis),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": ["dashboard_refresh_job"],
        }
        
        logger.info(f"✅ Dashboard refresh job completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Dashboard refresh job failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Refresh dashboard KPIs")
    parser.add_argument("--force", action="store_true", help="Force refresh even if data is recent")
    args = parser.parse_args()
    
    result = run_dashboard_refresh_job(force=args.force)
    print(f"Result: {result}")

