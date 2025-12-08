#!/usr/bin/env python3
"""
Script pour générer toutes les données nécessaires au préalable
Usage: python scripts/generate_data.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_all_data():
    """Génère toutes les données nécessaires"""
    logger.info("=" * 70)
    logger.info("🚀 Génération de toutes les données pour Finance Copilot")
    logger.info("=" * 70)
    
    results = {}
    
    # 1. Forecasts
    try:
        logger.info("\n📊 1/4 Génération des forecasts...")
        from jobs.forecasts import run_forecasts_job
        result = run_forecasts_job()
        results['forecasts'] = result
        if result.get('status') == 'completed':
            count = result.get('forecast_count', 0)
            logger.info(f"✅ Forecasts générés: {count} prévisions")
        else:
            logger.warning(f"⚠️  Forecasts: {result.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération des forecasts: {e}")
        results['forecasts'] = {'status': 'error', 'error': str(e)}
    
    # 2. News
    try:
        logger.info("\n📰 2/4 Génération du flux de news...")
        from jobs.news_ingest import run_news_ingest
        result = run_news_ingest()
        results['news'] = result
        if result.get('status') == 'completed':
            count = result.get('processed_count', 0)
            logger.info(f"✅ News générées: {count} articles")
        else:
            logger.warning(f"⚠️  News: {result.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération des news: {e}")
        results['news'] = {'status': 'error', 'error': str(e)}
    
    # 3. Weekly Brief
    try:
        logger.info("\n📋 3/4 Génération du brief hebdomadaire...")
        from jobs.weekly_brief import run_weekly_brief_job
        result = run_weekly_brief_job()
        results['brief'] = result
        if result.get('status') == 'completed':
            signals = result.get('top_signals', [])
            logger.info(f"✅ Brief généré: {len(signals)} signaux")
        else:
            logger.warning(f"⚠️  Brief: {result.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du brief: {e}")
        results['brief'] = {'status': 'error', 'error': str(e)}
    
    # 4. Intelligence Snapshot
    try:
        logger.info("\n🧠 4/4 Génération du snapshot d'intelligence...")
        from services.intelligence_service import get_market_intelligence_snapshot
        snapshot = get_market_intelligence_snapshot(use_cache=False, persist=True)
        results['intelligence'] = {'status': 'completed', 'snapshot': snapshot}
        logger.info("✅ Snapshot d'intelligence généré")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du snapshot: {e}")
        results['intelligence'] = {'status': 'error', 'error': str(e)}
    
    # Résumé
    logger.info("\n" + "=" * 70)
    logger.info("📊 RÉSUMÉ DE LA GÉNÉRATION")
    logger.info("=" * 70)
    for key, value in results.items():
        status = value.get('status', 'unknown')
        logger.info(f"  {key.upper():15} : {status}")
    
    # Vérification finale
    from storage.io import load_json
    logger.info("\n📁 Vérification des fichiers générés:")
    files_to_check = ['forecasts', 'news_feed', 'brief_weekly', 'intelligence_snapshot']
    for file_key in files_to_check:
        data = load_json(file_key)
        if data:
            if file_key == 'forecasts':
                count = len(data.get('rows', []))
                logger.info(f"  ✅ {file_key}: {count} éléments")
            elif file_key == 'news_feed':
                count = len(data.get('articles', []))
                logger.info(f"  ✅ {file_key}: {count} articles")
            elif file_key == 'brief_weekly':
                signals = data.get('top_signals', [])
                logger.info(f"  ✅ {file_key}: {len(signals)} signaux")
            else:
                logger.info(f"  ✅ {file_key}: présent")
        else:
            logger.warning(f"  ⚠️  {file_key}: absent ou vide")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ Génération terminée!")
    logger.info("=" * 70)
    
    return results

if __name__ == "__main__":
    try:
        results = generate_all_data()
        
        # Exit code basé sur les résultats
        all_ok = all(
            r.get('status') in ['completed', 'pending_dependencies']
            for r in results.values()
        )
        
        sys.exit(0 if all_ok else 1)
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}", exc_info=True)
        sys.exit(1)

