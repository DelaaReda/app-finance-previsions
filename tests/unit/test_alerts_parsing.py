"""
Tests unitaires pour la page Alerts - parsing et tri des issues
"""
from __future__ import annotations

import pandas as pd
import pytest


def test_parse_quality_issues():
    """Test du parsing et tri des issues de qualité."""
    # Simuler un report.json
    mock_report = {
        'news': {
            'issues': [
                {'sev': 'warn', 'msg': 'News stale'},
                {'sev': 'error', 'msg': 'News missing'}
            ]
        },
        'macro': {
            'issues': [
                {'sev': 'info', 'msg': 'Macro info'}
            ]
        },
        'prices': {
            'issues': []
        }
    }
    
    # Parser les issues
    issues = []
    for sec in ['news', 'macro', 'prices', 'forecasts', 'features', 'events']:
        s = mock_report.get(sec) or {}
        for it in (s.get('issues') or []):
            issues.append({'section': sec, **it})
    
    assert len(issues) == 3
    
    # Créer DataFrame et trier
    df = pd.DataFrame(issues)
    sev_order = {'error': 0, 'warn': 1, 'info': 2}
    df['sev_rank'] = df['sev'].map(lambda x: sev_order.get(str(x).lower(), 9))
    df = df.sort_values(['sev_rank', 'section'])
    
    # Vérifier l'ordre : error, warn, info
    assert df.iloc[0]['sev'] == 'error'
    assert df.iloc[1]['sev'] == 'warn'
    assert df.iloc[2]['sev'] == 'info'


def test_quality_csv_export():
    """Test de l'export CSV des issues."""
    df = pd.DataFrame([
        {'section': 'news', 'sev': 'error', 'msg': 'Test error'},
        {'section': 'macro', 'sev': 'warn', 'msg': 'Test warning'}
    ])
    
    # Export CSV
    csv_str = df.to_csv(index=False)
    
    assert 'section,sev,msg' in csv_str
    assert 'news,error,Test error' in csv_str
    assert 'macro,warn,Test warning' in csv_str
    assert len(csv_str) > 50  # Non vide


def test_moves_threshold_filter():
    """Test du filtrage des mouvements par seuil."""
    moves = [
        {'ticker': 'AAPL', 'd1': 0.025},   # 2.5%
        {'ticker': 'MSFT', 'd1': -0.008},  # -0.8%
        {'ticker': 'GOOGL', 'd1': 0.015},  # 1.5%
    ]
    
    df = pd.DataFrame(moves)
    df['d1_%'] = (df['d1'] * 100).round(2)
    
    # Seuil à 1.0%
    threshold = 1.0
    filtered = df[df['d1_%'].abs() >= threshold]
    
    assert len(filtered) == 2  # AAPL et GOOGL
    assert 'AAPL' in filtered['ticker'].values
    assert 'GOOGL' in filtered['ticker'].values
    assert 'MSFT' not in filtered['ticker'].values
