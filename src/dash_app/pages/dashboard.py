from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc
import dash


def _list_partitions(root: Path) -> list[str]:
    try:
        parts = []
        for p in sorted(root.glob('dt=*')):
            # accept dt=YYYYMMDD only
            s = p.name.split('=', 1)[-1]
            if s.isdigit():
                parts.append(s)
        return parts
    except Exception:
        return []


def _top_final(dt: str | None = None) -> dbc.Card:
    try:
        if dt:
            target = Path('data/forecast') / f'dt={dt}' / 'final.parquet'
            if not target.exists():
                return dbc.Card(dbc.CardBody([html.Small(f"Aucun final.parquet pour dt={dt}.")]))
            df = pd.read_parquet(target)
        else:
            parts = sorted(Path('data/forecast').glob('dt=*/final.parquet'))
            if not parts:
                return dbc.Card(dbc.CardBody([html.Small("Aucune donnée final.parquet trouvée.")]))
            df = pd.read_parquet(parts[-1])
        if df.empty:
            return dbc.Card(dbc.CardBody([html.Small("final.parquet vide.")]))
        top = df[df.get('horizon', pd.Series())=='1m'].sort_values('final_score', ascending=False).head(10)
        if top.empty or 'ticker' not in top.columns or 'final_score' not in top.columns:
            return dbc.Card(dbc.CardBody([html.Small("Données insuffisantes (colonnes manquantes).")]))
        table = dbc.Table.from_dataframe(top[['ticker','final_score']].reset_index(drop=True), striped=True, bordered=False, hover=True, size='sm')
        return dbc.Card([
            dbc.CardHeader("Top 10 (Final, 1m)"),
            dbc.CardBody(table),
        ])
    except Exception as e:
        return dbc.Card(dbc.CardBody([html.Small(f"Erreur lecture final: {e}")]))


def _top_commodities(dt: str | None = None) -> dbc.Card:
    """Display top commodity forecasts"""
    try:
        if dt:
            target = Path('data/forecast') / f'dt={dt}' / 'commodities.parquet'
            if not target.exists():
                # Fallback to latest available commodities parquet
                parts = sorted(Path('data/forecast').glob('dt=*/commodities.parquet'))
                if not parts:
                    return dbc.Card(dbc.CardBody([html.Small(f"Aucun commodities.parquet pour dt={dt}.")]))
                fallback = parts[-1]
                df = pd.read_parquet(fallback)
                fallback_dt = fallback.parent.name.split('=')[-1]
                note = html.Small(f"(dt {dt} indisponible, affichage dt={fallback_dt})", className="text-muted ms-2")
            else:
                df = pd.read_parquet(target)
                note = None
        else:
            parts = sorted(Path('data/forecast').glob('dt=*/commodities.parquet'))
            if not parts:
                return dbc.Card(dbc.CardBody([html.Small("Aucune donnée commodities.parquet trouvée.")]))
            df = pd.read_parquet(parts[-1])
            note = None

        if df.empty:
            return dbc.Card(dbc.CardBody([html.Small("commodities.parquet vide.")]))

        # Get top commodities by confidence for 1m horizon
        top = df[df.get('horizon', pd.Series())=='1m'].sort_values('confidence', ascending=False).head(5)

        if top.empty or 'commodity_name' not in top.columns or 'confidence' not in top.columns:
            return dbc.Card(dbc.CardBody([html.Small("Données insuffisantes (colonnes manquantes).")]))

        # Format display data
        display_data = []
        for _, row in top.iterrows():
            display_data.append({
                'Actif': row.get('commodity_name', 'N/A'),
                'Symbole': row.get('ticker', 'N/A'),
                'Prix': f"{row.get('current_price', 0):.2f}",
                'Confiance': f"{row.get('confidence', 0):.1%}",
                'Direction': row.get('direction', 'flat').upper()
            })

        table = dbc.Table.from_dataframe(
            pd.DataFrame(display_data),
            striped=True, bordered=False, hover=True, size='sm'
        )

        header_children = ["Top Commodities (1m)"]
        if note is not None:
            header_children.append(note)
        return dbc.Card([
            dbc.CardHeader(header_children),
            dbc.CardBody(table),
        ])
    except Exception as e:
        return dbc.Card(dbc.CardBody([html.Small(f"Erreur lecture commodities: {e}")]))


def _macro_kpis(dt: str | None = None) -> dbc.Card:
    try:
        base = Path('data/macro/forecast')
        fp: Path | None = None
        if dt:
            cand = base / f'dt={dt}' / 'macro_forecast.parquet'
            if cand.exists():
                fp = cand
        if fp is None:
            parts = sorted(base.glob('dt=*/macro_forecast.parquet'))
            if parts:
                fp = parts[-1]
        if fp is None or not fp.exists():
            return dbc.Card([dbc.CardHeader("Macro — KPIs"), dbc.CardBody([html.Small("Aucun macro_forecast.parquet trouvé.")])])
        df = pd.read_parquet(fp)
        if df is None or df.empty:
            return dbc.Card([dbc.CardHeader("Macro — KPIs"), dbc.CardBody([html.Small("macro_forecast.parquet vide.")])])

        # Heuristiques de colonnes
        def last(col: str):
            return df[col].dropna().iloc[-1] if col in df.columns and not df[col].dropna().empty else None

        # CPI / inflation
        cpi = last('cpi_yoy') or last('CPI_YoY') or last('cpi_yoy_pct') or last('inflation_yoy')
        # Yields and slope
        y10 = last('y10') or last('yield_10y')
        y2 = last('y2') or last('yield_2y')
        slope = (y10 - y2) if (y10 is not None and y2 is not None) else (last('slope_10y_2y') or last('yc_10y_2y') or last('yield_curve_slope'))
        rec = last('recession_prob') or last('recession_probability')

        items = []
        items.append(html.Small(f"CPI YoY: {cpi:.2f}%" if isinstance(cpi, (int, float)) else "CPI YoY: n/a"))
        items.append(html.Br())
        if isinstance(slope, (int, float)):
            items.append(html.Small(f"Pente 10Y-2Y: {slope:.2f} pp"))
        else:
            items.append(html.Small("Pente 10Y-2Y: n/a"))
        items.append(html.Br())
        if isinstance(rec, (int, float)):
            items.append(html.Small(f"Prob. récession (12m): {rec:.0%}"))
        else:
            items.append(html.Small("Prob. récession (12m): n/a"))

        return dbc.Card([dbc.CardHeader("Macro — KPIs"), dbc.CardBody(items)])
    except Exception as e:
        return dbc.Card([dbc.CardHeader("Macro — KPIs"), dbc.CardBody([html.Small(f"Erreur macro: {e}")])])


def _insights_card(dt: str | None = None) -> dbc.Card:
    try:
        # Count assets from final.parquet
        fp = None
        if dt:
            cand = Path('data/forecast') / f'dt={dt}' / 'final.parquet'
            if cand.exists():
                fp = cand
        if fp is None:
            parts = sorted(Path('data/forecast').glob('dt=*/final.parquet'))
            if parts:
                fp = parts[-1]

        assets = 0
        if fp and fp.exists():
            df = pd.read_parquet(fp)
            if not df.empty and 'ticker' in df.columns:
                assets = int(df['ticker'].nunique())

        # Freshness coverage and status
        parts = sorted(Path('data/quality').glob('dt=*/freshness.json'))
        cov_txt = "n/a"; status = dbc.Badge("Qualité: n/a", color="secondary")
        if parts:
            fresh = json.loads(parts[-1].read_text(encoding='utf-8'))
            checks = fresh.get('checks') or {}
            cov = checks.get('prices_5y_coverage_ratio')
            if isinstance(cov, (int, float)):
                cov_txt = f"{int(cov*100)}%"
                if cov >= 0.9:
                    status = dbc.Badge("Qualité: 🟢", color="success")
                elif cov >= 0.7:
                    status = dbc.Badge("Qualité: 🟡", color="warning")
                else:
                    status = dbc.Badge("Qualité: 🔴", color="danger")

        items = [
            html.Small(f"Actifs suivis (Final): {assets}"), html.Br(),
            html.Small(f"Couverture prix ≥5y: {cov_txt}"), html.Br(),
            status,
        ]
        return dbc.Card([dbc.CardHeader("📊 Insights rapides"), dbc.CardBody(items)])
    except Exception as e:
        return dbc.Card([dbc.CardHeader("📊 Insights rapides"), dbc.CardBody([html.Small(f"Erreur insights: {e}")])])


def _last_updated_label(default_dt: str | None) -> html.Small:
    try:
        def _fmt(dt: str) -> str:
            s = str(dt)
            if len(s) == 8 and s.isdigit():
                return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
            return s
        if default_dt:
            return html.Small(f"Dernière mise à jour: {_fmt(default_dt)}", id='dashboard-last-updated', className='text-muted ms-2')
        # fallback to latest dt from forecast
        parts = sorted(Path('data/forecast').glob('dt=*'))
        if parts:
            dt = parts[-1].name.split('=')[-1]
            return html.Small(f"Dernière mise à jour: {_fmt(dt)}", id='dashboard-last-updated', className='text-muted ms-2')
    except Exception:
        pass
    return html.Small("Dernière mise à jour: n/a", id='dashboard-last-updated', className='text-muted ms-2')


def layout():
    # Optional alerts badge (from latest quality report)
    badge = None
    try:
        parts = sorted(Path('data/quality').glob('dt=*/report.json'))
        if parts:
            rep = json.loads(parts[-1].read_text(encoding='utf-8'))
            def _count(rep, sev):
                cnt = 0
                for sec in ['news','macro','prices','forecasts','features','events','freshness']:
                    s = rep.get(sec) or {}
                    for it in (s.get('issues') or []):
                        if str(it.get('sev','')).lower() == sev:
                            cnt += 1
                return cnt
            errs = _count(rep, 'error'); warns = _count(rep, 'warn')
            badge = dbc.Badge(f"Errors: {errs}  Warnings: {warns}", color=("danger" if errs else ("warning" if warns else "success")), className="ms-2")
    except Exception:
        pass

    header = html.Div([html.H3("Dashboard — Top picks"), badge] if badge else [html.H3("Dashboard — Top picks")])

    # Partition selector
    dts = _list_partitions(Path('data/forecast'))
    default_dt = dts[-1] if dts else None
    controls = dbc.Row([
        dbc.Col([
            html.Small("Date (partition dt=YYYYMMDD) ", className="me-2"),
            dcc.Dropdown(
                id='dash-date-select',
                options=[{"label": x, "value": x} for x in dts],
                value=default_dt,
                placeholder="Sélectionner une date",
                clearable=True,
                style={"minWidth": "220px"},
            )
        ], md=4),
        dbc.Col([
            dbc.FormText("Filtrer sur ces tickers (format: AAPL,MSFT)"),
            html.Small("Watchlist: ", className="me-2"),
            dcc.Input(id='dash-watchlist', type='text', placeholder='ex: AAPL,MSFT', debounce=True, style={"minWidth":"240px"})
        ], md=4),
    ], className="mb-3")

    return html.Div([
        header,
        _last_updated_label(default_dt),
        controls,
        dbc.Row([
            dbc.Col(html.Div(id='dash-top-final', children=_top_final(default_dt)), md=6),
            dbc.Col(_top_commodities(default_dt), md=6),
        ], className="mb-3"),
        _insights_card(default_dt),
        _macro_kpis(default_dt),
    ], id='dashboard-root')


def _parse_watchlist(raw: str | None) -> list[str]:
    if not raw:
        return []
    items = [x.strip().upper() for x in str(raw).replace('\n', ',').split(',') if x.strip()]
    return list(dict.fromkeys(items))


@dash.callback(dash.Output('dash-top-final', 'children'), dash.Input('dash-date-select', 'value'), dash.Input('dash-watchlist','value'))
def on_dt_change(dt, wl):
    try:
        # Parse watchlist first
        watch = set(_parse_watchlist(wl)) if wl else set()

        # Get the appropriate final.parquet
        target = None
        if dt:
            target = Path('data/forecast') / f'dt={dt}' / 'final.parquet'
        else:
            parts = sorted(Path('data/forecast').glob('dt=*/final.parquet'))
            if parts:
                target = parts[-1]

        if not target or not target.exists():
            return dbc.Card(dbc.CardBody([html.Small("Aucun final.parquet trouvé.")]))

        df = pd.read_parquet(target)
        if df.empty:
            return dbc.Card(dbc.CardBody([html.Small("final.parquet vide.")]))

        # Filter by horizon and watchlist
        view = df[df.get('horizon') == '1m']
        if watch:
            view = view[view.get('ticker').isin(watch)]

        if view.empty:
            return dbc.Card([
                dbc.CardHeader(f"Top watchlist ({', '.join(sorted(watch))})" if watch else "Top 10 (Final, 1m)"),
                dbc.CardBody(dbc.Alert("Aucun ticker trouvé dans cette partition.", color="info"))
            ])

        # Sort and take top 10
        top = view.sort_values('final_score', ascending=False).head(10)

        if 'ticker' not in top.columns or 'final_score' not in top.columns:
            return dbc.Card(dbc.CardBody([html.Small("Colonnes ticker/final_score manquantes.")]))

        table = dbc.Table.from_dataframe(
            top[['ticker', 'final_score']].reset_index(drop=True),
            striped=True, bordered=False, hover=True, size='sm'
        )

        header_text = f"Top watchlist ({', '.join(sorted(watch))})" if watch else "Top 10 (Final, 1m)"
        return dbc.Card([dbc.CardHeader(header_text), dbc.CardBody(table)])

    except Exception as e:
        return dbc.Card(dbc.CardBody([html.Small(f"Erreur Dashboard: {e}")]))
