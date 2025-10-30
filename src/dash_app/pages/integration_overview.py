import os
import json
import glob
import pandas as pd
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc

# Import custom tools
from src.tools import parquet_io
from src.tools import make as make_tool # Renamed to avoid conflict with make

DEVTOOLS_ENABLED = os.environ.get("DEVTOOLS_ENABLED", "0") == "1"

if not DEVTOOLS_ENABLED:
    layout = html.Div(
        dbc.Alert("Cette page est uniquement disponible en mode développement.", color="info")
    )
else:
    # Helper function to find the latest dated directory
    def get_latest_dated_directory(base_path):
        list_of_dirs = glob.glob(os.path.join(base_path, "dt=*"))
        if not list_of_dirs:
            return None
        latest_dir = max(list_of_dirs, key=os.path.getctime)
        return latest_dir

    # 1. Top Prévisions (final.parquet)
    def get_top_previsions_layout():
        forecast_path = get_latest_dated_directory("data/forecast")
        if forecast_path:
            file_path = os.path.join(forecast_path, "final.parquet")
            try:
                df_forecast = parquet_io.read_parquet(file_path)
                if not df_forecast.empty:
                    # Ensure columns exist before selecting
                    required_cols = ['ticker', 'horizon', 'final_score']
                    if all(col in df_forecast.columns for col in required_cols):
                        df_display = df_forecast[required_cols].sort_values(by='final_score', ascending=False).head(10)
                        return html.Div([
                            html.H4("Top Prévisions (final.parquet)"),
                            dash_table.DataTable(
                                id='top-previsions-table',
                                columns=[{"name": i, "id": i} for i in df_display.columns],
                                data=df_display.to_dict('records'),
                                sort_action="native",
                                style_table={'overflowX': 'auto'}
                            )
                        ])
                    else:
                        return dbc.Alert(f"Le fichier de prévisions existe mais les colonnes requises ({', '.join(required_cols)}) sont manquantes.", color="warning")
                else:
                    return dbc.Alert("Le fichier de prévisions est vide.", color="info")
            except Exception as e:
                return dbc.Alert(f"Erreur lors du chargement des prévisions: {e}", color="danger")
        return dbc.Alert("Aucune donnée de prévisions disponible (data/forecast/dt=*/final.parquet).", color="info")

    # 2. Régime & Risque macro
    def get_macro_layout():
        macro_forecast_path = get_latest_dated_directory("data/macro/forecast")
        if macro_forecast_path:
            file_path_pattern = os.path.join(macro_forecast_path, "macro_forecast.*")
            macro_files = glob.glob(file_path_pattern)
            if macro_files:
                # For now, use placeholder values as exact logic is not defined
                regime_value = "Expansion" # Placeholder
                risk_value = "Modéré" # Placeholder
                return html.Div([
                    html.H4("Régime & Risque macro"),
                    dbc.Badge(f"Régime: {regime_value}", color="primary", className="me-1"),
                    dbc.Badge(f"Risque: {risk_value}", color="danger")
                ])
            else:
                return dbc.Alert("Aucun fichier de prévisions macro trouvé (data/macro/forecast/dt=*/macro_forecast.*).", color="info")
        return dbc.Alert("Aucune donnée de prévisions macro disponible (data/macro/forecast/dt=*/macro_forecast.*).", color="info")

    # 3. Synthèse LLM (llm_summary/summary.json)
    def get_llm_summary_layout():
        llm_summary_path = get_latest_dated_directory("data/llm_summary")
        if llm_summary_path:
            file_path = os.path.join(llm_summary_path, "summary.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                    summary_text = summary_data.get("summary", "Résumé non disponible.")
                    full_json_content = json.dumps(summary_data, indent=2, ensure_ascii=False)

                    return html.Div([
                        html.H4("Synthèse LLM (llm_summary/summary.json)"),
                        html.P(summary_text),
                        dcc.Markdown(
                            f"""
                            <details>
                            <summary>Sources LLM (cliquez pour développer)</summary>

                            ```json
                            {full_json_content}
                            ```
                            </details>
                            """,
                            dangerously_set_inner_html=True
                        )
                    ])
                except Exception as e:
                    return dbc.Alert(f"Erreur lors du chargement de la synthèse LLM: {e}", color="danger")
            else:
                return dbc.Alert("Fichier de synthèse LLM non trouvé (data/llm_summary/dt=*/summary.json).", color="info")
        return dbc.Alert("Aucune synthèse LLM disponible (data/llm_summary/dt=*/summary.json).", color="info")

    # 4. Action: "Relancer LLM summary" button
    llm_run_button_section = html.Div([
        html.H4("Action LLM"),
        dbc.Button("Relancer LLM summary", id="llm-run-button", color="primary", className="mb-3"),
        html.Pre(id="llm-run-output", children="Cliquez sur le bouton pour relancer la synthèse LLM.")
    ])

    layout = html.Div([
        html.H2("Vue d'ensemble de l'intégration (Développement)", className="mb-4"),
        dbc.Row([
            dbc.Col(get_top_previsions_layout(), md=6),
            dbc.Col(get_macro_layout(), md=6),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(get_llm_summary_layout(), md=6),
            dbc.Col(llm_run_button_section, md=6),
        ], className="mb-4"),
    ])