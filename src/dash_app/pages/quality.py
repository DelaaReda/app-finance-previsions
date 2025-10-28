from __future__ import annotations

from pathlib import Path
import json
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html
from dash_app.data.loader import read_parquet, read_json
from dash_app.data.paths import p_quality_anoms, p_quality_fresh


def _read_latest(glob_pat: str) -> tuple[dict | None, Path | None]:
    try:
        parts = sorted(Path('.').glob(glob_pat))
        if not parts:
            return (None, None)
        p = parts[-1]
        txt = p.read_text(encoding='utf-8')
        return (json.loads(txt), p)
    except Exception:
        return (None, None)


def _issues_table(rep: dict | None) -> dbc.Card:
    if not rep:
        return dbc.Card([dbc.CardHeader("Anomalies"), dbc.CardBody([html.Small("Aucun report.json — exécutez l'agent de qualité." )])])
    rows = []
    try:
        # rep might not be a dict; guard
        items = rep.items() if isinstance(rep, dict) else []
        for section, payload in items:
            issues = []
            if isinstance(payload, dict):
                issues = payload.get('issues') or []
            # Coerce to list
            if isinstance(issues, dict):
                issues = [issues]
            if isinstance(issues, str):
                issues = [{"msg": issues}]
            for it in issues or []:
                sev = 'n/a'
                msg = '—'
                if isinstance(it, dict):
                    sev = str(it.get('sev', '')).lower() or 'n/a'
                    msg = it.get('msg') or it.get('message') or '—'
                else:
                    msg = str(it)
                rows.append({'section': section, 'sev': sev, 'msg': msg})
    except Exception:
        rows = []
    if not rows:
        return dbc.Card([dbc.CardHeader("Anomalies"), dbc.CardBody([html.Small("Aucune anomalie listée dans le dernier rapport.")])])
    df = pd.DataFrame(rows)
    # Keep a compact view
    table = dbc.Table.from_dataframe(df[['section','sev','msg']].reset_index(drop=True), striped=True, bordered=False, hover=True, size='sm')
    return dbc.Card([dbc.CardHeader("Anomalies (dernier rapport)"), dbc.CardBody(table)])


def _summary_card(rep: dict | None, fresh: dict | None, rep_path: Path | None, fresh_path: Path | None) -> dbc.Card:
    body = []
    try:
        # Counts by severity
        errs = warns = 0
        if rep:
            for sec, payload in rep.items():
                for it in (payload or {}).get('issues') or []:
                    sev = str(it.get('sev','')).lower()
                    if sev == 'error':
                        errs += 1
                    elif sev in ('warn','warning'):
                        warns += 1
        body.append(html.Small(f"Erreurs: {errs}  Avertissements: {warns}"))
        body.append(html.Br())
        # Freshness quick flags
        checks = (fresh or {}).get('checks') or {}
        body.extend([
            html.Small(f"Forecasts aujourd'hui: {'Oui' if checks.get('forecasts_today') else 'Non'}"), html.Br(),
            html.Small(f"Final aujourd'hui: {'Oui' if checks.get('final_today') else 'Non'}"), html.Br(),
            html.Small(f"Macro aujourd'hui: {'Oui' if checks.get('macro_today') else 'Non'}"), html.Br(),
        ])
        cov = checks.get('prices_5y_coverage_ratio')
        body.append(html.Small(
            f"Couverture prix ≥5y: {int(cov*100)}%" if isinstance(cov, (int,float)) else "Couverture prix ≥5y: n/a"
        ))
        # Paths
        body.append(html.Br())
        body.append(html.Small(f"Rapport: {rep_path if rep_path else '—'}"))
        body.append(html.Br())
        body.append(html.Small(f"Freshness: {fresh_path if fresh_path else '—'}"))
    except Exception as e:
        body = [html.Small(f"Erreur résumé: {e}")]
    return dbc.Card([dbc.CardHeader("Résumé qualité & fraîcheur"), dbc.CardBody(body)])


def layout():
    # Prefer robust loader + path helpers
    # Keep report.json via legacy reader (structure is agent-specific)
    rep, rep_path = _read_latest('data/quality/dt=*/report.json')
    fresh = read_json(p_quality_fresh)
    fresh_path = p_quality_fresh()
    # Optional anomalies parquet (if agent writes it)
    anoms_df = read_parquet(p_quality_anoms)
    if anoms_df is not None and not anoms_df.empty:
        # Show aggregated anomalies as a compact table above issues
        try:
            g = (
                anoms_df.groupby(['dataset', 'severity'], as_index=False)['count']
                .sum().sort_values(['dataset', 'severity'])
            )
            agg_tbl = dbc.Table.from_dataframe(g, striped=True, bordered=False, hover=True, size='sm')
            anoms_card = dbc.Card([dbc.CardHeader("Anomalies (agrégées)"), dbc.CardBody(agg_tbl)], className="mb-3")
        except Exception:
            anoms_card = None
    else:
        anoms_card = None
    guide = html.Small([
        "Détails: ", html.A("Partitions & Freshness", href="https://github.com/DelaaReda/app-finance-previsions/blob/main/docs/PARTITIONS_FRESHNESS.md", target="_blank")
    ], className="text-muted")
    return html.Div([
        html.H3("Qualité des données"), guide,
        _summary_card(rep, fresh, rep_path, fresh_path),
        anoms_card or html.Div(),
        html.Div(className="mb-3"),
        _issues_table(rep),
    ])
