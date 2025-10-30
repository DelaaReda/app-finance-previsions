"""
Common UI components for Dash pages.
Reusable filters, badges, placeholders for graphs.
"""
from __future__ import annotations

import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd


def status_badge(status: str, label: str = "") -> dbc.Badge:
    """
    Create a status badge with consistent styling.
    
    Args:
        status: One of 'ok', 'warn', 'error', 'info'
        label: Optional text label
    
    Returns:
        dbc.Badge component
    """
    icons = {
        'ok': '✓',
        'warn': '⚠',
        'error': '✗',
        'info': 'ℹ'
    }
    colors = {
        'ok': 'success',
        'warn': 'warning',
        'error': 'danger',
        'info': 'secondary'
    }
    
    icon = icons.get(status, '?')
    color = colors.get(status, 'secondary')
    text = f"{icon} {label}" if label else icon
    
    return dbc.Badge(text, color=color, className="me-2")


def empty_figure(message: str = "Aucune donnée disponible") -> go.Figure:
    """
    Create a placeholder figure for empty data.
    
    Args:
        message: Message to display in the empty graph
    
    Returns:
        Plotly Figure with annotation
    """
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="#888")
    )
    fig.update_layout(
        template='plotly_dark',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=400,
    )
    return fig


def watchlist_filter(watchlist_id: str = 'watchlist-filter') -> dcc.Dropdown:
    """
    Create a watchlist dropdown filter.
    
    Args:
        watchlist_id: HTML id for the dropdown
    
    Returns:
        dcc.Dropdown component
    """
    # Read watchlist from env or file
    import os
    from pathlib import Path
    import json
    
    wl = os.getenv('WATCHLIST', '')
    if not wl:
        fp = Path('data/watchlist.json')
        if fp.exists():
            try:
                data = json.loads(fp.read_text(encoding='utf-8'))
                wl = ','.join(data.get('watchlist', []))
            except Exception:
                pass
    
    tickers = [t.strip().upper() for t in wl.split(',') if t.strip()]
    options = [{'label': t, 'value': t} for t in tickers]
    
    return dcc.Dropdown(
        id=watchlist_id,
        options=options,
        multi=True,
        placeholder="Filtrer par ticker",
        clearable=True,
        style={"minWidth": "200px"}
    )


def horizon_filter(horizon_id: str = 'horizon-filter') -> dcc.Dropdown:
    """
    Create a horizon dropdown filter.
    
    Args:
        horizon_id: HTML id for the dropdown
    
    Returns:
        dcc.Dropdown component
    """
    return dcc.Dropdown(
        id=horizon_id,
        options=[
            {'label': '1 semaine', 'value': '1w'},
            {'label': '1 mois', 'value': '1m'},
            {'label': '1 an', 'value': '1y'},
        ],
        value='1m',
        clearable=False,
        style={"minWidth": "160px"}
    )


def date_range_filter(date_range_id: str = 'date-range-filter') -> dcc.DatePickerRange:
    """
    Create a date range picker.
    
    Args:
        date_range_id: HTML id for the picker
    
    Returns:
        dcc.DatePickerRange component
    """
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    return dcc.DatePickerRange(
        id=date_range_id,
        start_date=start_date.date(),
        end_date=end_date.date(),
        display_format='YYYY-MM-DD',
        clearable=True,
        style={"minWidth": "280px"}
    )


def filter_row(*filters, label: str = "") -> dbc.Row:
    """
    Create a row of filters with consistent spacing.
    
    Args:
        *filters: Filter components to include
        label: Optional label for the filter row
    
    Returns:
        dbc.Row with filters
    """
    children = []
    if label:
        children.append(dbc.Col(html.Small(label), md=2))
    
    for f in filters:
        children.append(dbc.Col(f, md="auto"))
    
    return dbc.Row(children, className="mb-3 align-items-center")


def safe_dataframe_table(
    df: pd.DataFrame,
    table_id: str,
    columns: list[str] | None = None,
    page_size: int = 20,
    empty_message: str = "Aucune donnée"
) -> html.Div:
    """
    Create a DataTable with safe empty state handling.
    
    Args:
        df: DataFrame to display
        table_id: HTML id for the table
        columns: Optional list of column names to display
        page_size: Number of rows per page
        empty_message: Message for empty table
    
    Returns:
        html.Div with table or alert
    """
    from dash import dash_table
    
    if df is None or df.empty:
        return dbc.Alert(empty_message, color="info")
    
    # Select columns
    if columns:
        cols = [c for c in columns if c in df.columns]
        if not cols:
            return dbc.Alert("Colonnes requises introuvables", color="warning")
        df = df[cols]
    
    return dash_table.DataTable(
        id=table_id,
        columns=[{"name": c, "id": c} for c in df.columns],
        data=df.to_dict('records'),
        sort_action='native',
        filter_action='native',
        page_size=page_size,
        export_format='csv',
        export_headers='display',
        style_table={"overflowX": "auto"},
        style_cell={
            "fontSize": 13,
            "textAlign": "left",
            "padding": "8px"
        },
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#2b3035"
        },
    )
