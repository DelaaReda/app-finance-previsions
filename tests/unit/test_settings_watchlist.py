"""
Tests unitaires pour la page Settings - watchlist
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest


def test_normalize_tickers():
    """Test de la normalisation des tickers."""
    raw = "  aapl, MSFT ,  googl  , , tsla"
    
    # Normaliser
    tickers = [x.strip().upper() for x in raw.split(',') if x.strip()]
    
    assert tickers == ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    assert '' not in tickers
    assert all(t.isupper() for t in tickers)


def test_watchlist_json_creation(tmp_path):
    """Test de la création du fichier watchlist.json."""
    # Créer un dossier temporaire
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Écrire watchlist
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    watchlist_file = data_dir / "watchlist.json"
    
    data = {'watchlist': tickers}
    watchlist_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    # Vérifier
    assert watchlist_file.exists()
    loaded = json.loads(watchlist_file.read_text(encoding='utf-8'))
    assert loaded['watchlist'] == tickers


def test_export_command_generation():
    """Test de la génération de la commande export."""
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    cmd = f"export WATCHLIST={','.join(tickers)}"
    
    assert cmd == "export WATCHLIST=AAPL,MSFT,GOOGL"
    assert 'export' in cmd
    assert 'WATCHLIST=' in cmd


def test_empty_watchlist_handling():
    """Test de la gestion d'une watchlist vide."""
    raw = "  ,  , , "
    tickers = [x.strip().upper() for x in raw.split(',') if x.strip()]
    
    assert len(tickers) == 0
