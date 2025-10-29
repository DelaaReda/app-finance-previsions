"""
Tests d'intégration pour la page Settings - I/O watchlist
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pytest


def test_watchlist_file_read():
    """Test de lecture du fichier watchlist.json s'il existe."""
    p = Path('data/watchlist.json')
    
    if p.exists():
        data = json.loads(p.read_text(encoding='utf-8'))
        assert 'watchlist' in data
        assert isinstance(data['watchlist'], list)
        
        # Vérifier que les tickers sont en majuscules
        for ticker in data['watchlist']:
            assert ticker.isupper(), f"Ticker {ticker} n'est pas en majuscules"
    else:
        pytest.skip("data/watchlist.json n'existe pas")


def test_watchlist_env_fallback():
    """Test du fallback sur la variable d'environnement WATCHLIST."""
    watchlist_env = os.getenv('WATCHLIST')
    
    if watchlist_env:
        tickers = watchlist_env.split(',')
        assert len(tickers) > 0
        assert all(len(t.strip()) > 0 for t in tickers)
    else:
        pytest.skip("Variable WATCHLIST non définie")


def test_watchlist_write_read_cycle(tmp_path):
    """Test du cycle écriture/lecture de watchlist.json."""
    # Créer un dossier temporaire
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Écrire watchlist
    test_tickers = ['TEST1', 'TEST2', 'TEST3']
    watchlist_file = data_dir / "watchlist.json"
    
    data = {'watchlist': test_tickers}
    watchlist_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    # Relire
    loaded = json.loads(watchlist_file.read_text(encoding='utf-8'))
    
    assert loaded['watchlist'] == test_tickers
    assert len(loaded['watchlist']) == 3


def test_alerts_config_read():
    """Test de lecture du fichier alerts.json s'il existe."""
    p = Path('data/config/alerts.json')
    
    if p.exists():
        data = json.loads(p.read_text(encoding='utf-8'))
        
        # Vérifier structure attendue
        if 'move_abs_pct' in data:
            assert isinstance(data['move_abs_pct'], (int, float))
            assert 0.0 <= data['move_abs_pct'] <= 10.0
    else:
        pytest.skip("data/config/alerts.json n'existe pas")
