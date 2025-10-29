"""
Page Reports — Rapports générés
Affiche les rapports d'analyse générés par les agents.
"""
from __future__ import annotations

import json
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback


def layout() -> html.Div:
    """Layout principal de la page Reports."""
    return html.Div([
        html.H3("📋 Reports — Rapports d'analyse", className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Sélection")),
                    dbc.CardBody([
                        dbc.Label("Date:"),
                        dcc.Dropdown(
                            id='reports-date-dropdown',
                            placeholder="Sélectionnez une date...",
                        ),
                    ]),
                ]),
            ], width=3),
            
            dbc.Col([
                html.Div(id="reports-content"),
            ], width=9),
        ]),
    ])


@callback(
    Output("reports-date-dropdown", "options"),
    Output("reports-date-dropdown", "value"),
    Input("reports-date-dropdown", "id"),  # trigger on mount
)
def load_dates(_):
    """Charge les dates disponibles."""
    base = Path('data/reports')
    if not base.exists():
        return [], None
    
    dates = sorted([p.name for p in base.glob('dt=*')], reverse=True)
    options = [{'label': d, 'value': d} for d in dates]
    value = dates[0] if dates else None
    
    return options, value


@callback(
    Output("reports-content", "children"),
    Input("reports-date-dropdown", "value"),
)
def display_reports(date_folder):
    """Affiche les rapports disponibles."""
    if not date_folder:
        return dbc.Alert(
            "Sélectionnez une date pour afficher les rapports.",
            color="info"
        )
    
    try:
        reports_dir = Path('data/reports') / date_folder
        
        if not reports_dir.exists():
            return dbc.Alert(
                f"Aucun rapport trouvé pour {date_folder}.",
                color="warning"
            )
        
        # Find all JSON reports
        reports = sorted(reports_dir.glob('*.json'))
        
        if not reports:
            return dbc.Alert(
                "Aucun rapport JSON trouvé dans ce dossier.",
                color="info"
            )
        
        # Display each report in an accordion
        items = []
        for report_path in reports:
            try:
                obj = json.loads(report_path.read_text(encoding='utf-8'))
                
                # Try to extract meaningful content
                content = obj.get('content') or obj.get('answer') or obj.get('summary') or ""
                
                items.append(
                    dbc.AccordionItem([
                        dcc.Markdown(content) if content else html.Pre(
                            json.dumps(obj, indent=2, ensure_ascii=False),
                            style={
                                'backgroundColor': '#212529',
                                'color': '#00ff00',
                                'padding': '1rem',
                                'maxHeight': '400px',
                                'overflow': 'auto',
                            }
                        ),
                    ], title=report_path.stem)
                )
            except Exception as e:
                items.append(
                    dbc.AccordionItem([
                        dbc.Alert(f"Erreur lors de la lecture: {e}", color="warning"),
                    ], title=f"{report_path.stem} (erreur)")
                )
        
        return dbc.Accordion(items, start_collapsed=True)
    
    except Exception as e:
        return dbc.Alert(
            f"Erreur lors du chargement des rapports: {e}",
            color="danger"
        )
