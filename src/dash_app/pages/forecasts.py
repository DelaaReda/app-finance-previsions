from __future__ import annotations

from pathlib import Path
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, dash
import dash
try:
    from hub.logging_setup import get_logger  # type: ignore
    from hub import profiler as _prof  # type: ignore
    _log = get_logger("forecasts")  # type: ignore
except Exception:
    class _P:
        def log_event(self,*a,**k): pass
    class _L:
        def info(self,*a,**k): pass
        def debug(self,*a,**k): pass
        def exception(self,*a,**k): pass
    _prof = _P()  # type: ignore
    _log = _L()   # type: ignore


def _load_forecasts_data() -> pd.DataFrame:
    """Load latest equity forecasts data"""
    try:
        parts = sorted(Path('data/forecast').glob('dt=*'))
        if parts:
            latest = parts[-1]
            final_path = latest / 'final.parquet'
            if final_path.exists():
                return pd.read_parquet(final_path)
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame({'error': [f"Erreur chargement forecasts: {e}"]})


def _load_commodity_forecasts_data() -> pd.DataFrame:
    """Load latest commodity forecasts data"""
    try:
        parts = sorted(Path('data/forecast').glob('dt=*'))
        if parts:
            latest = parts[-1]
            commodities_path = latest / 'commodities.parquet'
            if commodities_path.exists():
                return pd.read_parquet(commodities_path)
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame({'error': [f"Erreur chargement commodities: {e}"]})


def layout():
    # Asset type selector
    asset_selector = dbc.Row([
        dbc.Col([
            html.Small("Type d'actif: "),
            dcc.Dropdown(
                id='forecasts-asset-type',
                options=[
                    {'label': 'Actions', 'value': 'equity'},
                    {'label': 'Matières Premières', 'value': 'commodity'},
                    {'label': 'Tous', 'value': 'all'}
                ],
                value='all',
                clearable=False,
                style={"minWidth": "200px"}
            )
        ], md=4),
    ], className="mb-3")

    # Controls
    controls = dbc.Row([
        dbc.Col([
            html.Small("Filtre par horizon: "),
            dcc.Dropdown(
                id='forecasts-horizon-filter',
                options=[
                    {'label': 'Tous', 'value': 'all'},
                    {'label': '1 semaine', 'value': '1w'},
                    {'label': '1 mois', 'value': '1m'},
                    {'label': '1 an', 'value': '1y'}
                ],
                value='all',
                clearable=False,
                style={"minWidth": "150px"}
            )
        ], md=3),
        dbc.Col([
            html.Small("Recherche: "),
            dcc.Input(id='forecasts-search', type='text', placeholder='AAPL, Gold, Oil...', value='NGD.TO, OR, Gold', debounce=True)
        ], md=3),
        dbc.Col([
            html.Small("Trier par: "),
            dcc.Dropdown(
                id='forecasts-sort-by',
                options=[
                    {'label': 'Score/Confiance', 'value': 'score'},
                    {'label': 'Nom', 'value': 'name'},
                    {'label': 'Horizon', 'value': 'horizon'}
                ],
                value='score',
                clearable=False,
                style={"minWidth": "150px"}
            )
        ], md=3),
    ], className="mb-3")

    return html.Div([
        html.H3("Forecasts - Prévisions Multi-Actifs"),
        asset_selector,
        controls,
        html.Div(id='forecasts-content', className="mb-3"),
    ])


@dash.callback(
    dash.Output('forecasts-content', 'children'),
    dash.Input('forecasts-asset-type', 'value'),
    dash.Input('forecasts-horizon-filter', 'value'),
    dash.Input('forecasts-search', 'value'),
    dash.Input('forecasts-sort-by', 'value')
)
def update_forecasts(asset_type, horizon, search, sort_by):
    try:
        _prof.log_event("callback", {"id": "forecasts.update", "asset_type": asset_type, "horizon": horizon, "sort_by": sort_by, "search": search})
        _log.debug("forecasts.update.start", extra={"ctx": {"asset_type": asset_type, "horizon": horizon, "sort_by": sort_by, "search": search}})
        # Load data based on asset type
        if asset_type == 'equity':
            df = _load_forecasts_data()
            asset_name = "Actions"
        elif asset_type == 'commodity':
            df = _load_commodity_forecasts_data()
            asset_name = "Matières Premières"
        else:  # 'all'
            # Load both datasets
            equity_df = _load_forecasts_data()
            commodity_df = _load_commodity_forecasts_data()

            # Combine them
            if not equity_df.empty and 'error' not in equity_df.columns:
                equity_df['asset_type'] = 'equity'
                if not commodity_df.empty and 'error' not in commodity_df.columns:
                    commodity_df['asset_type'] = 'commodity'
                    df = pd.concat([equity_df, commodity_df], ignore_index=True)
                else:
                    df = equity_df
            elif not commodity_df.empty and 'error' not in commodity_df.columns:
                commodity_df['asset_type'] = 'commodity'
                df = commodity_df
            else:
                df = pd.DataFrame()

        if df.empty or 'error' in df.columns:
            return dbc.Alert("Aucune prévision disponible.", color="warning")

        # Filter by horizon
        if horizon != 'all':
            df = df[df['horizon'] == horizon]

        # Filter by search
        if search:
            search_terms = [t.strip().lower() for t in search.split(',') if t.strip()]
            mask = pd.Series(False, index=df.index)
            for term in search_terms:
                # Search in ticker, commodity_name, or category
                if 'commodity_name' in df.columns:
                    mask |= df['ticker'].str.lower().str.contains(term, na=False)
                    mask |= df['commodity_name'].str.lower().str.contains(term, na=False)
                    mask |= df['category'].str.lower().str.contains(term, na=False)
                else:
                    mask |= df['ticker'].str.lower().str.contains(term, na=False)
            df = df[mask]

        if df.empty:
            return dbc.Alert("Aucune prévision trouvée avec ces critères.", color="info")

        # Sort based on asset type
        if asset_type == 'commodity' or (asset_type == 'all' and 'confidence' in df.columns):
            # For commodities, sort by confidence
            sort_column = 'confidence' if 'confidence' in df.columns else 'expected_return'
            df = df.sort_values(sort_column, ascending=False)
        elif 'final_score' in df.columns:
            # For equity, sort by final_score
            df = df.sort_values('final_score', ascending=False)
        else:
            # Default sort by expected_return
            df = df.sort_values('expected_return', ascending=False)

        # Prepare display data based on asset type
        if asset_type == 'commodity' or (asset_type == 'all' and 'commodity_name' in df.columns):
            # Commodity display format
            display_columns = ['commodity_name', 'ticker', 'category', 'horizon', 'current_price', 'expected_price', 'expected_return', 'direction', 'confidence', 'unit']
            available_columns = [col for col in display_columns if col in df.columns]

            display_df = df[available_columns].copy()
            display_df['confidence'] = display_df['confidence'].fillna(0).apply(lambda x: f"{x:.1%}")
            display_df['expected_return'] = display_df['expected_return'].fillna(0).apply(lambda x: f"{x:.2%}")
            display_df['current_price'] = display_df['current_price'].fillna(0).apply(lambda x: f"{x:.2f}")
            display_df['expected_price'] = display_df['expected_price'].fillna(0).apply(lambda x: f"{x:.2f}")

            # Rename columns for display
            display_df = display_df.rename(columns={
                'commodity_name': 'Nom',
                'ticker': 'Symbole',
                'category': 'Catégorie',
                'horizon': 'Horizon',
                'current_price': 'Prix Actuel',
                'expected_price': 'Prix Cible',
                'expected_return': 'Rendement Attendu',
                'direction': 'Direction',
                'confidence': 'Confiance',
                'unit': 'Unité'
            })
        else:
            # Equity display format
            display_df = df[['ticker', 'horizon', 'final_score', 'direction', 'confidence', 'expected_return']].copy()
            display_df['confidence'] = display_df['confidence'].fillna(0).apply(lambda x: f"{x:.1%}")
            display_df['expected_return'] = display_df['expected_return'].fillna(0).apply(lambda x: f"{x:.2%}")
            display_df['final_score'] = display_df['final_score'].fillna(0).apply(lambda x: f"{x:.2f}")

            # Rename columns for display
            display_df = display_df.rename(columns={
                'ticker': 'Symbole',
                'horizon': 'Horizon',
                'final_score': 'Score Final',
                'direction': 'Direction',
                'confidence': 'Confiance',
                'expected_return': 'Rendement Attendu'
            })

        # Create table
        table = html.Div(
            dbc.Table.from_dataframe(
                display_df.reset_index(drop=True),
                striped=True, bordered=False, hover=True, size='sm'
            ), id='forecasts-table'
        )

        # Summary
        summary_items = []
        summary_items.append(html.Li(f"Total prévisions: {len(df)}"))

        if 'commodity_name' in df.columns:
            summary_items.append(html.Li(f"Actifs uniques: {df['commodity_name'].nunique()}"))
            summary_items.append(html.Li(f"Catégories: {', '.join(df['category'].unique())}"))
        else:
            summary_items.append(html.Li(f"Tickers uniques: {df['ticker'].nunique()}"))

        summary_items.append(html.Li(f"Horizons: {', '.join(df['horizon'].unique())}"))

        # Calculate average score/confidence
        if 'final_score' in df.columns:
            try:
                avg_score = float(df['final_score'].mean())
                summary_items.append(html.Li(f"Score moyen: {avg_score:.2f}"))
            except Exception:
                pass
        elif 'confidence' in df.columns:
            try:
                avg_confidence = float(df['confidence'].mean())
                summary_items.append(html.Li(f"Confiance moyenne: {avg_confidence:.1%}"))
            except Exception:
                pass

        content = dbc.Card([
            dbc.CardHeader(f"Prévisions {asset_name} ({len(df)} résultats)"),
            dbc.CardBody([
                table,
                html.Hr(),
                dbc.Card([
                    dbc.CardHeader("Résumé"),
                    dbc.CardBody(html.Ul(summary_items))
                ])
            ])
        ])

        _log.info("forecasts.update.ok", extra={"ctx": {"rows": int(len(df)), "asset_type": asset_type}})
        return content

    except Exception as e:
        _prof.log_event("error", {"where": "forecasts.update", "error": str(e)})
        _log.exception("forecasts.update.fail", extra={"ctx": {"error": str(e)}})
        return dbc.Alert(f"Erreur affichage prévisions: {e}", color="danger")
