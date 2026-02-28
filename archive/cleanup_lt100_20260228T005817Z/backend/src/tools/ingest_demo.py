#!/usr/bin/env python3
"""
Script d'ingestion de démonstration.
Simule l'ingestion de données depuis différentes sources.
"""
import sys
from pathlib import Path
import asyncio
import pandas as pd
from datetime import datetime, timedelta

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_ingestion_demo():
    """Exécute la démonstration d'ingestion de données."""
    print("🔄 Démarrage de la démonstration d'ingestion...")
    
    # 1. Ingestion depuis Yahoo Finance
    print("\n📊 Ingestion des données boursières (Yahoo Finance)...")
    from core.market_data import get_price_history
    
    tickers = ["SPY", "QQQ", "AAPL", "NVDA"]
    for ticker in tickers:
        print(f"   Téléchargement des données pour {ticker}...")
        try:
            df = get_price_history(ticker, start=datetime.now() - timedelta(days=30))
            if df is not None and not df.empty:
                print(f"   ✅ {ticker}: {len(df)} lignes téléchargées")
            else:
                print(f"   ⚠️  {ticker}: Aucune donnée disponible")
        except Exception as e:
            print(f"   ❌ {ticker}: Erreur - {e}")
    
    # 2. Ingestion depuis FRED
    print("\n📈 Ingestion des données macroéconomiques (FRED)...")
    from core.market_data import get_fred_series
    
    series_ids = ["CPIAUCSL", "VIXCLS", "DGS10"]
    for series_id in series_ids:
        print(f"   Téléchargement de la série {series_id}...")
        try:
            df = get_fred_series(series_id)
            if df is not None and not df.empty:
                print(f"   ✅ {series_id}: {len(df)} points téléchargés")
            else:
                print(f"   ⚠️  {series_id}: Aucune donnée disponible")
        except Exception as e:
            print(f"   ❌ {series_id}: Erreur - {e}")
    
    # 3. Ingestion des news
    print("\n📰 Ingestion des actualités financières...")
    from ingestion.finnews import run_pipeline
    
    try:
        items = run_pipeline(
            regions=["US"],
            window="last_day",
            limit=10
        )
        print(f"   ✅ {len(items)} articles de news téléchargés et traités")
    except Exception as e:
        print(f"   ❌ Erreur d'ingestion des news - {e}")
    
    # 4. Génération des prévisions
    print("\n🔮 Génération des prévisions...")
    from analytics.forecaster import forecast_ticker
    
    for ticker in ["SPY", "QQQ"]:
        for horizon in ["1w", "1m"]:
            try:
                forecast = forecast_ticker(ticker, horizon)
                print(f"   ✅ {ticker} ({horizon}): {forecast.direction} avec {forecast.confidence:.2f} confiance")
            except Exception as e:
                print(f"   ❌ {ticker} ({horizon}): Erreur - {e}")
    
    # 5. Sauvegarde dans le stockage
    print("\n💾 Sauvegarde des données dans le stockage parquet...")
    from agents.forecast_aggregator_agent import aggregate
    
    try:
        result_path = aggregate()
        if result_path:
            print(f"   ✅ Données de prévision agrégées sauvegardées: {result_path}")
        else:
            print("   ⚠️  Aucune donnée de prévision à agrégée")
    except Exception as e:
        print(f"   ❌ Erreur lors de l'agrégation - {e}")
    
    print(f"\n🏁 Démonstration d'ingestion terminée à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    run_ingestion_demo()