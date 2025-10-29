"""
Tests UI pour la page Alerts
"""
from __future__ import annotations

import pytest
from dash.testing.application_runners import import_app


def test_alerts_page_render(dash_duo):
    """Test du rendu de la page Alerts."""
    # Importer l'app
    app = import_app("dash_app.app")
    dash_duo.start_server(app)
    
    # Naviguer vers /alerts
    dash_duo.wait_for_page(url="http://localhost:8050/alerts", timeout=10)
    
    # Vérifier les éléments clés
    dash_duo.wait_for_element("#alerts-quality-body", timeout=5)
    dash_duo.wait_for_element("#alerts-threshold", timeout=5)
    dash_duo.wait_for_element("#alerts-moves-content", timeout=5)
    
    # Vérifier qu'il n'y a pas d'erreurs console
    assert dash_duo.get_logs() == [], "Erreurs console détectées"


def test_alerts_threshold_slider(dash_duo):
    """Test de l'interaction avec le slider de seuil."""
    app = import_app("dash_app.app")
    dash_duo.start_server(app)
    
    dash_duo.wait_for_page(url="http://localhost:8050/alerts", timeout=10)
    
    # Attendre le slider
    slider = dash_duo.wait_for_element("#alerts-threshold", timeout=5)
    assert slider is not None
    
    # Le slider devrait avoir une valeur par défaut
    # (test simple de présence, pas d'interaction complexe)


def test_alerts_quality_table(dash_duo):
    """Test de la présence de la table de qualité."""
    app = import_app("dash_app.app")
    dash_duo.start_server(app)
    
    dash_duo.wait_for_page(url="http://localhost:8050/alerts", timeout=10)
    
    # Vérifier la section qualité
    quality_body = dash_duo.wait_for_element("#alerts-quality-body", timeout=5)
    assert quality_body is not None


def test_alerts_earnings_section(dash_duo):
    """Test de la section earnings."""
    app = import_app("dash_app.app")
    dash_duo.start_server(app)
    
    dash_duo.wait_for_page(url="http://localhost:8050/alerts", timeout=10)
    
    # Vérifier le slider earnings
    earnings_slider = dash_duo.wait_for_element("#alerts-earnings-days", timeout=5)
    assert earnings_slider is not None
    
    # Vérifier le contenu earnings
    earnings_content = dash_duo.wait_for_element("#alerts-earnings-content", timeout=5)
    assert earnings_content is not None
