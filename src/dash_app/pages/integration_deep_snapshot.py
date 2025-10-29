import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import pandas as pd
import json
from pathlib import Path
import os

from src.tools.parquet_io import read_parquet_latest
from src.core.config import Config

# Initialize config
config = Config()

# Check if devtools are enabled
DEVTOOLS_ENABLED = os.getenv("DEVTOOLS_ENABLED", "0") == "1"

dash.register_page(__name__, path="/integration_deep_snapshot", name="Deep Ticker Snapshot", order=999,
                   extra_template_variables={"DEVTOOLS_ENABLED": DEVTOOLS_ENABLED})

layout = html.Div(
    [
        dcc.Store(id="store-forecast-data"),
        dcc.Store(id="store-llm-summary-data"),
        html.H2("Deep Ticker Snapshot (DevTools)", className="mb-4"),
        dbc.Alert(
            "Cette page est uniquement disponible lorsque DEVTOOLS_ENABLED=1.",
            color="warning",
            className="mb-3",
            is_open=not DEVTOOLS_ENABLED,
            duration=60000,
        ),
        html.Div(
            [
                dbc.Label("Entrez un symbole boursier (ex: AAPL):"),
                dcc.Input(
                    id="ticker-input",
                    type="text",
                    placeholder="AAPL",
                    debounce=True,
                    className="form-control mb-4",
                    style={"width": "200px"}
                ),
            ],
            className="mb-4"
        ),
        html.H3("Prévisions Filtrées", className="mb-3"),
        html.Div(id="forecast-table-container", className="mb-5"),
        html.H3("Justification LLM", className="mb-3"),
        html.Div(id="llm-justification-container"),
    ],
    className="container-fluid mt-4"
)

@dash.callback(
    Output("store-forecast-data", "data"),
    Input("ticker-input", "value")
)
def load_forecast_data(ticker_value):
    if not DEVTOOLS_ENABLED:
        return None

    forecast_path = config.get_data_path("forecast")
    df = read_parquet_latest(forecast_path, "final.parquet")
    if df is None or df.empty:
        return None
    return df.to_dict("records")

@dash.callback(
    Output("store-llm-summary-data", "data"),
    Input("ticker-input", "value")
)
def load_llm_summary_data(ticker_value):
    if not DEVTOOLS_ENABLED:
        return None

    llm_summary_base_path = config.get_data_path("llm_summary")
    latest_llm_summary_dir = read_parquet_latest(llm_summary_base_path, "") # Use empty string to get latest dir
    
    if latest_llm_summary_dir:
        summary_file = Path(latest_llm_summary_dir.parent) / latest_llm_summary_dir.name / "summary.json"
        if summary_file.exists():
            with open(summary_file, "r") as f:
                return json.load(f)
    return None

@dash.callback(
    Output("forecast-table-container", "children"),
    Input("ticker-input", "value"),
    Input("store-forecast-data", "data")
)
def update_forecast_table(ticker_value, forecast_data):
    if not DEVTOOLS_ENABLED:
        return html.Div()

    if not ticker_value or not forecast_data:
        return dbc.Alert(
            "Aucune prévision disponible pour ce symbole boursier ou données manquantes.",
            color="info",
            className="mt-3"
        )

    df = pd.DataFrame(forecast_data)
    filtered_df = df[df["ticker"].str.upper() == ticker_value.upper()]

    if filtered_df.empty:
        return dbc.Alert(
            f"Aucune prévision trouvée pour le symbole boursier '{ticker_value}'.",
            color="info",
            className="mt-3"
        )

    return dash_table.DataTable(
        id="forecast-table",
        columns=[
            {"name": col, "id": col} for col in ["horizon", "final_score", "direction"]
        ],
        data=filtered_df[["horizon", "final_score", "direction"]].to_dict("records"),
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "8px",
            "fontFamily": "Arial, sans-serif",
        },
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold",
        },
    )

@dash.callback(
    Output("llm-justification-container", "children"),
    Input("ticker-input", "value"),
    Input("store-llm-summary-data", "data")
)
def update_llm_justification(ticker_value, llm_summary_data):
    if not DEVTOOLS_ENABLED:
        return html.Div()

    if not ticker_value or not llm_summary_data:
        return dbc.Alert(
            "Aucune justification LLM disponible pour ce symbole boursier ou données manquantes.",
            color="info",
            className="mt-3"
        )

    contributors = llm_summary_data.get("contributors", [])
    relevant_contributors = [
        c for c in contributors if c.get("ticker", "").upper() == ticker_value.upper()
    ]

    if not relevant_contributors:
        return dbc.Alert(
            f"Aucune justification LLM trouvée pour le symbole boursier '{ticker_value}'.",
            color="info",
            className="mt-3"
        )

    justifications = []
    for contributor in relevant_contributors:
        justifications.append(
            html.Div(
                [
                    html.H5(f"Contributeur: {contributor.get('name', 'N/A')}"),
                    html.P(f"Rôle: {contributor.get('role', 'N/A')}"),
                    html.P(f"Justification: {contributor.get('justification', 'N/A')}"),
                    html.Hr()
                ],
                className="mb-3 p-3 border rounded"
            )
        )
    return html.Div(justifications)
