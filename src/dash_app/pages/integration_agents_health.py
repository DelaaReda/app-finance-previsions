import os
import json
from datetime import datetime, timedelta
from pathlib import Path

import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc

from src.tools.parquet_io import latest_partition, read_parquet_latest
from src.tools.make import run_make # This will be used in callbacks, but imported here for conceptual completeness

# --- Configuration ---
DEVTOOLS_ENABLED = os.environ.get("DEVTOOLS_ENABLED", "0") == "1"

# Agent configurations
AGENTS_CONFIG = {
    "Equities": {
        "freshness_key": "equity_forecast_agent",
        "output_path": "data/forecast", # Check for dt=*/equity_forecast.parquet
        "output_filename": "equity_forecast.parquet",
        "make_target": "equity-forecast",
    },
    "Aggregator": {
        "freshness_key": "forecast_aggregator_agent",
        "output_path": "data/forecast",
        "output_filename": "final.parquet",
        "make_target": "forecast-aggregate",
    },
    "Macro": {
        "freshness_key": "macro_forecast_agent",
        "output_path": "data/macro/forecast",
        "output_filename": "macro_forecast.parquet", # Assuming .parquet or .json, checking for .parquet
        "make_target": "macro-forecast",
    },
    "LLM": {
        "freshness_key": "llm_summary_agent",
        "output_path": "data/llm_summary",
        "output_filename": "summary.json",
        "make_target": "llm-summary-run",
    },
    "Quality": {
        "freshness_key": "data_quality_agent",
        "output_path": "data/quality", # Check for dt=*/freshness.json itself
        "output_filename": "freshness.json",
        "make_target": "update-monitor", # This is the make target for the quality agent
    },
}

# --- Helper Functions ---

def get_latest_freshness_data():
    """Reads the latest freshness.json file."""
    freshness_dir = Path("data/quality")
    latest_dt_path = latest_partition(freshness_dir)
    if latest_dt_path:
        freshness_file = latest_dt_path / "freshness.json"
        if freshness_file.exists():
            with open(freshness_file, "r") as f:
                return json.load(f)
    return {}

def get_agent_status(agent_name, config, freshness_data):
    """Determines the status, latest partition, and age for a given agent."""
    status_emoji = "🔴" # Red by default
    latest_dt_str = "N/A"
    age_hours = "N/A"
    status_text = "Données manquantes"

    # Check freshness from freshness.json
    freshness_info = freshness_data.get(config["freshness_key"])
    if freshness_info and freshness_info.get("latest_dt"):
        latest_dt_str = freshness_info["latest_dt"]
        try:
            # Handle both YYYYMMDD and YYYYMMDDHH formats
            if len(latest_dt_str) == 8:
                latest_dt = datetime.strptime(latest_dt_str, "%Y%m%d")
            elif len(latest_dt_str) == 10:
                latest_dt = datetime.strptime(latest_dt_str, "%Y%m%d%H")
            else:
                raise ValueError("Format de date/heure inconnu")

            now = datetime.now()
            age_timedelta = now - latest_dt
            age_hours = int(age_timedelta.total_seconds() / 3600)

            # Determine status based on age (example thresholds)
            if age_hours < 24:
                status_emoji = "🟢" # Green if less than 24 hours old
                status_text = "À jour"
            elif age_hours < 72:
                status_emoji = "🟡" # Yellow if 24-72 hours old
                status_text = "Potentiellement obsolète"
            else:
                status_emoji = "🔴" # Red if older than 72 hours
                status_text = "Obsolète"

        except ValueError:
            status_text = "Erreur de format de date"
            status_emoji = "🔴"
    else:
        status_text = "Pas de données de fraîcheur"
        status_emoji = "🔴"

    # Additionally, check for the existence of the expected output file
    output_exists = False
    if config["output_path"] and config["output_filename"]:
        output_base_dir = Path(config["output_path"])
        output_latest_dt_path = latest_partition(output_base_dir)
        if output_latest_dt_path:
            expected_output_file = output_latest_dt_path / config["output_filename"]
            if expected_output_file.exists():
                output_exists = True
            else:
                status_text = "Fichier de sortie manquant"
                status_emoji = "🔴"
        else:
            status_text = "Partition de sortie manquante"
            status_emoji = "🔴"
    
    # If freshness data exists but output file is missing, it's red
    if freshness_info and not output_exists:
        status_emoji = "🔴"
        status_text = "Fichier de sortie manquant"
    elif not freshness_info and output_exists:
        # If output exists but no freshness info, it's yellow (data might be old but present)
        status_emoji = "🟡"
        status_text = "Données de fraîcheur manquantes"
    elif not freshness_info and not output_exists:
        status_emoji = "🔴"
        status_text = "Données et fichier de sortie manquants"


    return {
        "Agent": agent_name,
        "Statut": f"{status_emoji} {status_text}",
        "Dernière partition": latest_dt_str,
        "Âge (heures)": age_hours,
    }

# --- Layout ---

if DEVTOOLS_ENABLED:
    freshness_data = get_latest_freshness_data()
    agent_health_data = [
        get_agent_status(name, config, freshness_data)
        for name, config in AGENTS_CONFIG.items()
    ]

    layout = html.Div(
        [
            html.H2("Panneau de Santé des Agents (DEV)", className="mb-4"),

            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("Vue d'ensemble du statut des agents", className="card-title"),
                        dash_table.DataTable(
                            id="agent-status-table",
                            columns=[{"name": i, "id": i} for i in agent_health_data[0].keys()],
                            data=agent_health_data,
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
                        ),
                    ]
                ),
                className="mb-4",
            ),

            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("Actions de Développement", className="card-title"),
                        html.Div(
                            [
                                dbc.Button(
                                    agent_config["make_target"].replace("-", " ").title(),
                                    id=f"btn-{agent_config['make_target']}",
                                    className="me-2 mb-2",
                                    n_clicks=0,
                                )
                                for agent_config in AGENTS_CONFIG.values()
                            ],
                            className="mb-3",
                        ),
                        dcc.Loading(
                            id="loading-output",
                            type="default",
                            children=html.Div(id="make-output-log", children=html.Pre("Logs des commandes make..."))
                        ),
                    ]
                ),
                className="mb-4",
            ),
        ],
        className="container-fluid mt-4",
    )
else:
    layout = html.Div(
        dbc.Alert(
            "Les outils de développement ne sont pas activés. Définissez DEVTOOLS_ENABLED=1 pour accéder à cette page.",
            color="warning",
            className="mt-4",
        )
    )

# Callbacks for buttons will be implemented in src/dash_app/app.py