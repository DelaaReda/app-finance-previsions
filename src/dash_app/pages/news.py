from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, dash
from dash import dash_table
import dash
try:
    from hub.logging_setup import get_logger  # type: ignore
    from hub import profiler as _prof  # type: ignore
    _log = get_logger("news")  # type: ignore
except Exception:
    class _P:
        def log_event(self,*a,**k): pass
    class _L:
        def info(self,*a,**k): pass
        def debug(self,*a,**k): pass
        def exception(self,*a,**k): pass
    _prof = _P()  # type: ignore
    _log = _L()   # type: ignore


def _load_news_data() -> pd.DataFrame:
    """Load latest news data from JSONL or fallback to sample"""
    try:
        # Try to load from latest news partition
        parts = sorted(Path('data/news').glob('dt=*'))
        if parts:
            latest = parts[-1]
            files = sorted(latest.glob('news_*.parquet'))
            if files:
                return pd.read_parquet(files[-1])

        # Fallback to news.jsonl
        if Path('data/news.jsonl').exists():
            return pd.read_json('data/news.jsonl', lines=True)

        # Sample data fallback
        return pd.DataFrame({
            'title': ['Sample News 1', 'Sample News 2'],
            'summary': ['Sample summary 1', 'Sample summary 2'],
            'source': ['Source 1', 'Source 2'],
            'published': [pd.Timestamp.now(), pd.Timestamp.now()],
            'sentiment': ['positive', 'negative'],
            'tickers': [['AAPL'], ['MSFT']]
        })
    except Exception as e:
        return pd.DataFrame({'error': [f"Erreur chargement news: {e}"]})


def _news_summary(df: pd.DataFrame) -> str:
    """Generate AI summary of news (placeholder)"""
    if df.empty or 'error' in df.columns:
        return "Aucune actualité disponible."

    # Simple summary based on sentiment
    positive = len(df[df.get('sentiment') == 'positive'])
    negative = len(df[df.get('sentiment') == 'negative'])
    total = len(df)

    return f"Synthèse: {total} articles analysés. {positive} positifs, {negative} négatifs. Focus sur les tendances marché récentes."


def layout():
    # Controls
    controls = dbc.Row([
        dbc.Col([
            html.Small("Filtre par secteur: "),
            dcc.Dropdown(
                id='news-sector-filter',
                options=[
                    {'label': 'Tous', 'value': 'all'},
                    {'label': 'Technologie', 'value': 'tech'},
                    {'label': 'Finance', 'value': 'finance'},
                    {'label': 'Énergie', 'value': 'energy'}
                ],
                value='all',
                clearable=False,
                style={"minWidth": "200px"}
            )
        ], md=4),
        dbc.Col([
            html.Small("Recherche: "),
            dcc.Input(id='news-search', type='text', placeholder='Mots-clés...', debounce=True)
        ], md=4),
    ], className="mb-3")

    return html.Div([
        html.H3("News & Agrégation"),
        controls,
        html.Div(id='news-summary', className="mb-3"),
        html.Div(id='news-table', className="mb-3"),
        html.Div(id='news-details', className="mb-3"),
    ])


@dash.callback(
    dash.Output('news-summary', 'children'),
    dash.Output('news-table', 'children'),
    dash.Input('news-sector-filter', 'value'),
    dash.Input('news-search', 'value')
)
def update_news(sector, search):
    try:
        _prof.log_event("callback", {"id": "news.update", "sector": sector, "search": search})
        _log.debug("news.update.start", extra={"ctx": {"sector": sector, "search": search}})
        df = _load_news_data()

        if df.empty or 'error' in df.columns:
            return (
                dbc.Alert("Aucune actualité disponible.", color="warning"),
                dbc.Alert("Erreur lors du chargement des actualités.", color="danger")
            )

        # Filter by sector (placeholder logic)
        if sector != 'all':
            # Simple sector filtering based on tickers or content
            sector_tickers = {
                'tech': ['AAPL', 'MSFT', 'GOOGL', 'AMZN'],
                'finance': ['JPM', 'BAC', 'WFC', 'GS'],
                'energy': ['XOM', 'CVX', 'COP', 'SLB']
            }
            if sector in sector_tickers:
                df = df[df.get('tickers', []).apply(lambda x: any(t in sector_tickers[sector] for t in x) if x else False)]

        # Filter by search
        if search:
            df = df[df.get('title', '').str.contains(search, case=False, na=False) |
                    df.get('summary', '').str.contains(search, case=False, na=False)]

        # Summary
        summary_text = _news_summary(df)
        summary_card = dbc.Card([
            dbc.CardHeader("Synthèse IA des Actualités"),
            dbc.CardBody(html.P(summary_text))
        ])

        # Table
        if not df.empty:
            # Prepare display data
            display_df = df[['title', 'summary', 'source', 'published', 'sentiment']].copy()
            display_df['published'] = pd.to_datetime(display_df['published'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
            display_df['sentiment'] = display_df['sentiment'].fillna('neutral')

            table = dash_table.DataTable(
                id='news-table-dt',
                columns=[{"id": c, "name": c} for c in display_df.columns],
                data=display_df.reset_index(drop=True).to_dict('records'),
                sort_action='native', filter_action='native', page_size=15,
                export_format='csv', style_table={'overflowX':'auto'},
                style_cell={'padding':'6px','textAlign':'left','minWidth':'120px'}
            )
            table_card = dbc.Card([
                dbc.CardHeader(f"Actualités ({len(df)} articles)"),
                dbc.CardBody(table)
            ])
        else:
            table_card = dbc.Alert("Aucune actualité trouvée avec ces critères.", color="info")

        _log.info("news.update.ok", extra={"ctx": {"rows": int(len(df))}})
        return summary_card, table_card

    except Exception as e:
        _prof.log_event("error", {"where": "news.update", "error": str(e)})
        _log.exception("news.update.fail", extra={"ctx": {"error": str(e)}})
        return (
            dbc.Alert("Erreur génération synthèse.", color="danger"),
            dbc.Alert(f"Erreur affichage actualités: {e}", color="danger")
        )
