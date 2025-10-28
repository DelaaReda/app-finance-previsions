from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import dash_bootstrap_components as dbc
from dash import html, dcc, dash, Input, Output, State
from dash import dash_table
import dash


def _load_ticker_data(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load price data, forecasts, and news for a ticker"""
    ticker = ticker.strip().upper()

    # Load price data
    prices_path = Path(f'data/prices/ticker={ticker}/prices.parquet')
    prices_df = pd.DataFrame()
    if prices_path.exists():
        prices_df = pd.read_parquet(prices_path)
        if not prices_df.empty:
            prices_df = prices_df.set_index('date').sort_index()

    # Load forecasts for this ticker
    forecasts_df = pd.DataFrame()
    try:
        parts = sorted(Path('data/forecast').glob('dt=*'))
        if parts:
            latest = parts[-1]
            final_path = latest / 'final.parquet'
            if final_path.exists():
                final_df = pd.read_parquet(final_path)
                forecasts_df = final_df[final_df['ticker'] == ticker].copy()
    except Exception:
        pass

    # Load news for this ticker (placeholder)
    news_df = pd.DataFrame({
        'title': [f'News sample for {ticker}'],
        'summary': ['Sample news summary'],
        'sentiment': ['neutral'],
        'published': [pd.Timestamp.now()]
    })

    return prices_df, forecasts_df, news_df


def _create_price_chart(prices_df: pd.DataFrame) -> dcc.Graph:
    """Create 5-year price chart. Accepts either 'close' or 'Close' columns."""
    if prices_df.empty:
        return dcc.Graph(figure=go.Figure().add_annotation(text="Aucune donnée de prix disponible", showarrow=False))

    price_col = 'close' if 'close' in prices_df.columns else ('Close' if 'Close' in prices_df.columns else None)
    if price_col is None:
        return dcc.Graph(figure=go.Figure().add_annotation(text="Colonne de prix introuvable (close/Close)", showarrow=False))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices_df.index, y=prices_df[price_col], mode='lines', name='Prix de clôture'))

    # Add simple moving averages if enough data
    if len(prices_df) >= 20:
        prices_df['SMA_20'] = prices_df[price_col].rolling(20).mean()
        fig.add_trace(go.Scatter(x=prices_df.index, y=prices_df['SMA_20'], mode='lines', name='SMA 20j'))

    if len(prices_df) >= 50:
        prices_df['SMA_50'] = prices_df[price_col].rolling(50).mean()
        fig.add_trace(go.Scatter(x=prices_df.index, y=prices_df['SMA_50'], mode='lines', name='SMA 50j'))

    fig.update_layout(
        title=f"Cours de l'action (5 ans)",
        xaxis_title="Date",
        yaxis_title="Prix",
        template='plotly_dark',
        height=400
    )

    return dcc.Graph(figure=fig)


def _create_forecasts_table(forecasts_df: pd.DataFrame) -> dbc.Table:
    """Create forecasts table"""
    if forecasts_df.empty:
        return dbc.Alert("Aucune prévision disponible pour ce ticker.", color="info")

    # Prepare display data
    display_df = forecasts_df[['horizon', 'final_score', 'direction', 'confidence', 'expected_return']].copy()
    display_df['confidence'] = display_df['confidence'].fillna(0).apply(lambda x: f"{x:.1%}")
    display_df['expected_return'] = display_df['expected_return'].fillna(0).apply(lambda x: f"{x:.2%}")

    return dbc.Table.from_dataframe(
        display_df.reset_index(drop=True),
        striped=True, bordered=False, hover=True, size='sm'
    )


def _create_news_section(news_df: pd.DataFrame) -> html.Div:
    """Create news section"""
    if news_df.empty:
        return dbc.Alert("Aucune actualité disponible pour ce ticker.", color="info")

    news_items = []
    for _, row in news_df.head(3).iterrows():
        sentiment_color = {
            'positive': 'success',
            'negative': 'danger',
            'neutral': 'secondary'
        }.get(row.get('sentiment', 'neutral'), 'secondary')

        news_items.append(
            dbc.Card([
                dbc.CardHeader([
                    html.Small(row.get('published', '').strftime('%Y-%m-%d') if hasattr(row.get('published', ''), 'strftime') else str(row.get('published', ''))),
                    dbc.Badge(row.get('sentiment', 'neutral').title(), color=sentiment_color, className="ms-2")
                ]),
                dbc.CardBody([
                    html.H6(row.get('title', ''), className="card-title"),
                    html.P(row.get('summary', ''), className="card-text")
                ])
            ], className="mb-2")
        )

    return html.Div([
        html.H5("Actualités récentes"),
        html.Div(news_items)
    ])


def _load_fundamentals(ticker: str) -> dict:
    base = Path(f'data/fundamentals/ticker={ticker}')
    if not base.exists():
        return {}
    files = sorted(base.glob('*.json'))
    if not files:
        return {}
    import json
    try:
        return json.loads(files[-1].read_text(encoding='utf-8'))
    except Exception:
        return {}


def _fundamentals_card(ticker: str) -> dbc.Card:
    js = _load_fundamentals(ticker)
    if not js:
        return dbc.Card([dbc.CardHeader("Fondamentaux"), dbc.CardBody(html.Small("Aucun fondamental disponible."))], className="mb-3")
    keys = [
        ('market_cap','Market Cap'), ('pe_ratio','P/E'), ('debt_to_equity','Debt/Equity'),
        ('roe','ROE'), ('roa','ROA'), ('dividend_yield','Dividende'), ('beta','Beta')
    ]
    items = []
    for k, label in keys:
        if k in js:
            val = js[k]
            try:
                if isinstance(val, (int,float)):
                    if any(x in k for x in ['yield','roe','roa']):
                        val = f"{float(val):.2%}"
                    else:
                        val = f"{float(val):,.0f}"
            except Exception:
                pass
            items.append(html.Li([html.Small(f"{label}: {val}")]))
    body = html.Ul(items) if items else html.Small("Clés standards non trouvées.")
    return dbc.Card([dbc.CardHeader("Fondamentaux"), dbc.CardBody(body)], className="mb-3")


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return pd.DataFrame({'macd': macd, 'signal': signal_line, 'hist': hist})


def _peers_table(ticker: str) -> dbc.Card:
    try:
        import json
        wl = []
        wf = Path('data/watchlist.json')
        if wf.exists():
            obj = json.loads(wf.read_text(encoding='utf-8'))
            wl = [x for x in (obj.get('watchlist') or []) if isinstance(x, str)]
        peers = [x for x in wl if x.upper() != ticker.upper()]
        if not peers:
            peers = ['ABX.TO','K.TO','AEM.TO','OR','GDX']
        rows = []
        for t in peers[:12]:
            p = Path(f'data/prices/ticker={t}/prices.parquet')
            if not p.exists():
                continue
            try:
                df = pd.read_parquet(p)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    df = df.set_index('date').sort_index()
                col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                if not col:
                    continue
                s = df[col].dropna()
                if len(s) < 60:
                    continue
                def ret(days):
                    idx = max(0, len(s)-days)
                    return float(s.iloc[-1] / s.iloc[idx] - 1)
                rows.append({'ticker': t, 'ret_1m': ret(21), 'ret_3m': ret(63), 'ret_1y': ret(252)})
            except Exception:
                continue
        if not rows:
            return dbc.Card([dbc.CardHeader("Comparables"), dbc.CardBody(html.Small("Aucun pair trouvé avec prix suffisants."))], className="mb-3")
        dfp = pd.DataFrame(rows)
        tbl = dash_table.DataTable(
            id='deep-dive-peers',
            columns=[{"id": c, "name": c} for c in dfp.columns],
            data=dfp.sort_values('ret_1m', ascending=False).to_dict('records'),
            export_format='csv', page_size=10,
            style_table={'overflowX':'auto'}, style_cell={'padding':'6px', 'fontSize':12}
        )
        return dbc.Card([dbc.CardHeader("Comparables (perf 1m/3m/1y)"), dbc.CardBody(tbl)], className="mb-3")
    except Exception:
        return dbc.Card([dbc.CardHeader("Comparables"), dbc.CardBody(html.Small("Erreur calcul comparables."))], className="mb-3")


def _render_ticker_sections(ticker: str):
    try:
        ticker = (ticker or 'NGD.TO').strip().upper()
        prices_df, forecasts_df, news_df = _load_ticker_data(ticker)

        if prices_df.empty and forecasts_df.empty and news_df.empty:
            return dbc.Alert(f"Aucune donnée disponible pour le ticker {ticker}.", color="warning")

        sections = []
        if not prices_df.empty:
            sections.append(dbc.Card([
                dbc.CardHeader("Cours de l'action (5 ans)"),
                dbc.CardBody(_create_price_chart(prices_df))
            ], className="mb-3"))

        if not forecasts_df.empty:
            sections.append(dbc.Card([
                dbc.CardHeader(f"Prévisions pour {ticker}"),
                dbc.CardBody(_create_forecasts_table(forecasts_df))
            ], className="mb-3"))

        sections.append(dbc.Card([
            dbc.CardHeader(f"Actualités pour {ticker}"),
            dbc.CardBody(_create_news_section(news_df))
        ], className="mb-3"))

        # Fundamentals & Peers
        sections.append(_fundamentals_card(ticker))
        sections.append(_peers_table(ticker))

        # LLM verdict card (if available)
        try:
            import json
            base = Path('data/forecast')
            parts = sorted(base.glob('dt=*/llm_agents.json'))
            verdict = None
            if parts:
                js = json.loads(parts[-1].read_text(encoding='utf-8'))
                for t in (js.get('tickers') or []):
                    if (t.get('ticker') or '').upper() == ticker.upper():
                        m = (t.get('models') or [{}])[0]
                        verdict = {
                            'provider': m.get('name') or m.get('source') or 'llm',
                            'direction': m.get('direction') or '—',
                            'expected_return': m.get('expected_return'),
                            'confidence': m.get('confidence')
                        }
                        break
            if verdict:
                body = html.Ul([
                    html.Li(html.Small(f"Provider: {verdict['provider']}")),
                    html.Li(html.Small(f"Direction: {verdict['direction']}")),
                    html.Li(html.Small(f"Exp. Return: {float(verdict['expected_return']):.2%}" if isinstance(verdict.get('expected_return'), (int,float)) else "Exp. Return: —")),
                    html.Li(html.Small(f"Confidence: {float(verdict['confidence']):.1%}" if isinstance(verdict.get('confidence'), (int,float)) else "Confidence: —")),
                ])
            else:
                body = html.Small("Aucun verdict LLM.")
        except Exception:
            body = html.Small("Erreur lecture verdict LLM.")
        # Explain (show latest context JSON) button + modal
        explain_btn = html.Div([
            dbc.Button("Explain (LLM Context)", id='deep-dive-explain-btn', size='sm', className='mb-2'),
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle(f"Contexte LLM — {ticker}")),
                dbc.ModalBody(id='deep-dive-explain-body'),
                dbc.ModalFooter(dbc.Button("Fermer", id='deep-dive-explain-close', className='ms-auto'))
            ], id='deep-dive-explain-modal', is_open=False, size='xl')
        ])

        sections.append(dbc.Card([dbc.CardHeader("Verdict LLM"), dbc.CardBody([body, explain_btn])], className="mb-3", id='deep-dive-llm'))

        # Technicals
        if not prices_df.empty:
            col = 'close' if 'close' in prices_df.columns else ('Close' if 'Close' in prices_df.columns else None)
            if col:
                s = prices_df[col].dropna()
                rsi_val = _rsi(s).iloc[-1] if len(s) > 30 else None
                macd_df = _macd(s).tail(1) if len(s) > 30 else None
                tech_items = []
                if rsi_val is not None:
                    tech_items.append(html.Li(f"RSI(14): {rsi_val:.1f}"))
                if macd_df is not None and not macd_df.empty:
                    tech_items.append(html.Li(f"MACD: {macd_df['macd'].iloc[-1]:.2f} / Signal: {macd_df['signal'].iloc[-1]:.2f}"))
                sections.append(dbc.Card([dbc.CardHeader("Techniques"), dbc.CardBody(html.Ul(tech_items or [html.Small("Indicateurs indisponibles.")]))], className="mb-3"))

        return html.Div(sections)
    except Exception as e:
        return dbc.Alert(f"Erreur lors de l'analyse du ticker {ticker}: {e}", color="danger")


def layout():
    # Try to seed a multi-ticker list from latest final.parquet
    tickers = []
    try:
        parts = sorted(Path('data/forecast').glob('dt=*/final.parquet'))
        if parts:
            df = pd.read_parquet(parts[-1])
            if 'ticker' in df.columns:
                tickers = sorted(df['ticker'].dropna().astype(str).unique().tolist())[:500]
    except Exception:
        tickers = []

    default_ticker = 'NGD.TO'
    return html.Div([
        html.H3("Deep Dive - Analyse d'un titre"),
        # Single ticker analyzer (legacy)
        dbc.Row([
            dbc.Col([
                html.Small("Entrez un ticker (ex: AAPL, MSFT): "),
                dcc.Input(id='deep-dive-ticker', type='text', placeholder='NGD.TO', value=default_ticker, debounce=True, style={"minWidth": "200px"}),
                html.Button("Analyser", id='deep-dive-analyze', n_clicks=0, className="ms-2 btn btn-primary")
            ], md=8)
        ], className="mb-3"),
        html.Div(id='deep-dive-content', children=_render_ticker_sections(default_ticker)),
        html.Hr(),
        # Multi tickers comparator
        html.H4("Comparaison multi‑tickers"),
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(
                    id='dd-tickers',
                    options=[{"label": t, "value": t} for t in tickers],
                    multi=True,
                    placeholder="Choisir 1..N tickers",
                )
            ], md=6),
            dbc.Col([
                dcc.DatePickerRange(id='dd-range')
            ], md=4),
            dbc.Col([
                dcc.Checklist(
                    id='dd-normalize',
                    options=[{"label": "Normaliser (base 100)", "value": "norm"}],
                    value=["norm"], inline=True,
                )
            ], md=2),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(dcc.Graph(id='dd-prices'), md=12)
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id='dd-prices-norm'), md=12)
        ])
    ])


@dash.callback(
    dash.Output('deep-dive-content', 'children'),
    dash.Input('deep-dive-analyze', 'n_clicks'),
    dash.State('deep-dive-ticker', 'value')
)
def analyze_ticker(n_clicks, ticker):
    # Default to NGD.TO if nothing provided, and allow initial render
    ticker = (ticker or 'NGD.TO').strip().upper()
    return _render_ticker_sections(ticker)


@dash.callback(
    dash.Output('deep-dive-explain-modal', 'is_open'),
    dash.Output('deep-dive-explain-body', 'children'),
    dash.Input('deep-dive-explain-btn', 'n_clicks'),
    dash.Input('deep-dive-explain-close', 'n_clicks'),
    dash.State('deep-dive-explain-modal', 'is_open'),
    dash.State('deep-dive-ticker', 'value')
)
def toggle_explain(n_open, n_close, is_open, ticker):
    # Open -> load latest context JSON for ticker; Close -> just toggle
    import json as _json
    ticker = (ticker or 'NGD.TO').strip().upper()
    ctx_txt = "(contexte introuvable)"
    try:
        base = Path('data/llm/context')
        parts = sorted(base.glob('dt=*'))
        if parts:
            fp = parts[-1] / f"{ticker}.json"
            if fp.exists():
                ctx_txt = fp.read_text(encoding='utf-8')[:120000]
    except Exception:
        pass
    triggered = dash.callback_context.triggered[0]['prop_id'] if dash.callback_context and dash.callback_context.triggered else ''
    if 'deep-dive-explain-btn' in triggered:
        return True, html.Pre(ctx_txt, style={'maxHeight':'60vh','overflowY':'auto'})
    elif 'deep-dive-explain-close' in triggered:
        return False, dash.no_update
    return is_open, dash.no_update


# === Multi‑tickers overlay ===

def _load_price_series(ticker: str) -> pd.DataFrame:
    p = Path(f'data/prices/ticker={ticker}/prices.parquet')
    if not p.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(p)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.set_index('date').sort_index()
        col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
        if not col:
            return pd.DataFrame()
        return df[[col]].rename(columns={col: 'close'})
    except Exception:
        return pd.DataFrame()


@dash.callback(
    Output('dd-prices', 'figure'),
    Output('dd-prices-norm', 'figure'),
    Input('dd-tickers', 'value'),
    Input('dd-range', 'start_date'),
    Input('dd-range', 'end_date'),
    Input('dd-normalize', 'value')
)
def _update_multi_prices(tickers, start_date, end_date, normalize_flags):
    try:
        tickers = tickers or []
        if not tickers:
            return {}, {}
        frames = []
        for t in tickers:
            df = _load_price_series(str(t))
            if df.empty:
                continue
            sub = df.copy()
            if start_date:
                sub = sub[sub.index >= pd.to_datetime(start_date)]
            if end_date:
                sub = sub[sub.index <= pd.to_datetime(end_date)]
            sub = sub.rename(columns={'close': t})
            frames.append(sub)
        if not frames:
            return {}, {}
        wide = pd.concat(frames, axis=1).dropna(how='all')
        # Regular prices chart
        fig1 = px.line(wide, x=wide.index, y=wide.columns, title="Prix (overlay)")
        fig1.update_layout(hovermode='x unified', template='plotly_dark')

        # Normalized chart
        if 'norm' in (normalize_flags or []):
            norm = wide.apply(lambda s: (s / s.dropna().iloc[0]) * 100.0)
            fig2 = px.line(norm, x=norm.index, y=norm.columns, title="Prix normalisés (base 100)")
            fig2.update_layout(hovermode='x unified', template='plotly_dark')
        else:
            fig2 = {}
        return fig1, fig2
    except Exception:
        return {}, {}
