from __future__ import annotations

from pathlib import Path
import json
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html


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
        for section, payload in rep.items():
            issues = (payload or {}).get('issues') or []
            for it in issues:
                rows.append({
                    'section': section,
                    'sev': str(it.get('sev','')).lower() or 'n/a',
                    'msg': it.get('msg') or it.get('message') or '—',
                })
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
    rep, rep_path = _read_latest('data/quality/dt=*/report.json')
    fresh, fresh_path = _read_latest('data/quality/dt=*/freshness.json')
    guide = html.Small([
        "Détails: ", html.A("Partitions & Freshness", href="https://github.com/DelaaReda/app-finance-previsions/blob/main/docs/PARTITIONS_FRESHNESS.md", target="_blank")
    ], className="text-muted")
    return html.Div([
        html.H3("Qualité des données"), guide,
        _summary_card(rep, fresh, rep_path, fresh_path),
        html.Div(className="mb-3"),
        _issues_table(rep),
    ])
