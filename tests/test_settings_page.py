"""
Tests UI pour la page Settings
"""
from __future__ import annotations

import pytest
from dash.testing.application_runners import import_app


def test_settings_page_render(dash_duo):
    """Test du rendu de la page Settings."""
    # Importer l'app
    app = import_app("dash_app.app")
    dash_duo.start_server(app)
    
    # Naviguer vers /settings
    dash_duo.wait_for_page(url="http://localhost:8050/settings", timeout=10)
    
    # Vérifier les éléments clés
    dash_duo.wait_for_element("#settings-watchlist-textarea", timeout=5)
    dash_duo.wait_for_element("#settings-save-btn", timeout=5)
    dash_duo.wait_for_element("#settings-export-btn", timeout=5)
    
    # Vérifier qu'il n'y a pas d'erreurs console
    assert dash_duo.get_logs() == [], "Erreurs console détectées"


def test_settings_textarea_present(dash_duo):
    """Test de la présence du textarea pour éditer la watchlist."""
    app = import_app("dash_app.app")
    dash_duo.start_server(app)
    
    dash_duo.wait_for_page(url="http://localhost:8050/settings", timeout=10)
    
    # Attendre le textarea
    textarea = dash_duo.wait_for_element("#settings-watchlist-textarea", timeout=5)
    assert textarea is not None
    
    # Le textarea devrait avoir du contenu par défaut
    value = textarea.get_attribute('value')
    assert value is not None


def test_settings_buttons_present(dash_duo):
    """Test de la présence des boutons Save et Export."""
    app = import_app("dash_app.app")
    dash_duo.start_server(app)
    
    dash_duo.wait_for_page(url="http://localhost:8050/settings", timeout=10)
    
    # Vérifier bouton Save
    save_btn = dash_duo.wait_for_element("#settings-save-btn", timeout=5)
    assert save_btn is not None
    assert "Enregistrer" in save_btn.text
    
    # Vérifier bouton Export
    export_btn = dash_duo.wait_for_element("#settings-export-btn", timeout=5)
    assert export_btn is not None
    assert "export" in export_btn.text.lower()


def test_settings_feedback_area(dash_duo):
    """Test de la présence de la zone de feedback."""
    app = import_app("dash_app.app")
    dash_duo.start_server(app)
    
    dash_duo.wait_for_page(url="http://localhost:8050/settings", timeout=10)
    
    # Les divs de feedback devraient exister (même vides initialement)
    feedback = dash_duo.find_element("#settings-feedback")
    assert feedback is not None
    
    export_cmd = dash_duo.find_element("#settings-export-command")
    assert export_cmd is not None
