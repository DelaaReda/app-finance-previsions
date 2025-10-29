"""
Page LLM Models — G4F Working List
Affiche la liste des modèles LLM fonctionnels testés via g4f.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dash_table, Input, Output, State, callback


def layout() -> html.Div:
    """Layout principal de la page LLM Models."""
    return html.Div([
        html.H3("🧠 LLM Models — G4F Working List", className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Actions")),
                    dbc.CardBody([
                        html.P("Tester les modèles:"),
                        dbc.Label("Limite à tester:"),
                        dcc.Slider(
                            id='llm-models-limit-slider',
                            min=2,
                            max=12,
                            step=1,
                            value=6,
                            marks={i: str(i) for i in range(2, 13, 2)},
                            className="mb-3"
                        ),
                        dbc.Button(
                            "🔄 Tester modèles (rapide)",
                            id="llm-models-test-btn",
                            color="primary",
                            className="w-100"
                        ),
                        html.Small(
                            "Utilise g4f; essaie quelques providers. Peut prendre 1-2 minutes.",
                            className="text-muted mt-2"
                        ),
                        html.Div(id="llm-models-test-feedback", className="mt-3"),
                    ]),
                ]),
            ], width=3),
            
            dbc.Col([
                html.Div(id="llm-models-table-container"),
            ], width=9),
        ]),
    ])


@callback(
    Output("llm-models-table-container", "children"),
    Input("llm-models-table-container", "id"),  # trigger on mount
    Input("llm-models-test-btn", "n_clicks"),  # refresh after test
)
def render_models_table(_, n_clicks):
    """Affiche la table des modèles testés."""
    try:
        p = Path('data/llm/models/working.json')
        
        if not p.exists():
            return dbc.Alert(
                "Aucun fichier working.json trouvé. Utilisez le bouton 'Tester modèles (rapide)'.",
                color="info"
            )
        
        obj = json.loads(p.read_text(encoding='utf-8'))
        asof = obj.get('asof', 'N/A')
        models = obj.get('models') or []
        
        if not models:
            return dbc.Alert(
                "La liste est vide. Utilisez le bouton 'Tester modèles (rapide)'.",
                color="info"
            )
        
        df = pd.DataFrame(models)
        
        # Sort by ok, pass_rate, latency
        if 'ok' in df.columns:
            df = df.sort_values(
                by=['ok', 'pass_rate', 'latency_s'],
                ascending=[False, False, True]
            )
        
        return html.Div([
            dbc.Alert(f"Dernière mise à jour: {asof}", color="info", className="mb-3"),
            
            dash_table.DataTable(
                columns=[
                    {"name": col.replace('_', ' ').title(), "id": col}
                    for col in df.columns
                ],
                data=df.to_dict('records'),
                style_cell={'textAlign': 'left', 'padding': '8px'},
                style_header={'backgroundColor': '#343a40', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{ok} = True'},
                        'backgroundColor': '#28a745',
                        'color': 'white',
                    },
                    {
                        'if': {'filter_query': '{ok} = False'},
                        'backgroundColor': '#dc3545',
                        'color': 'white',
                    },
                ],
                page_size=20,
                sort_action="native",
                filter_action="native",
            ),
        ])
    
    except Exception as e:
        return dbc.Alert(f"Erreur lors du chargement des modèles: {e}", color="warning")


@callback(
    Output("llm-models-test-feedback", "children"),
    Input("llm-models-test-btn", "n_clicks"),
    State("llm-models-limit-slider", "value"),
    prevent_initial_call=True,
)
def test_models(n_clicks, limit):
    """Lance le test des modèles."""
    try:
        from agents.g4f_model_watcher import refresh
        
        # This will take time - show loading state
        p = refresh(limit=limit, refresh_verified=True)
        
        return dbc.Alert(
            f"✓ Mise à jour écrite: {p}",
            color="success"
        )
    
    except Exception as e:
        return dbc.Alert(
            f"❌ Échec mise à jour: {e}",
            color="danger"
        )


# Import missing dcc
from dash import dcc
