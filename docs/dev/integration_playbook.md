# Integration Playbook — Dash Pages (DEV‑only, safe)

Ce guide décrit comment ajouter/étendre des pages Dash en respectant les conventions du projet, sans impacter l’UI de production. Les pages d’intégration sont utilisées pour expérimenter ou préparer une migration.

## Vision & Principes

- UI Dash = lecture/filtre/affichage — pas de compute lourd ni d’accès réseau.
- Données lisibles via partitions immuables: `data/<domaine>/dt=YYYYMMDD/…` (ou horaire `dt=YYYYMMDDHH`).
- Zéro duplication: réutiliser les loaders / fonctions existantes; si une page existe déjà, ne pas la re‑créer.

## Garde‑fous (DEV vs PROD)

- Pages d’intégration: toujours sous `src/dash_app/pages/integration_<nom>.py`.
- Affichage uniquement en DEV: exporter `DEVTOOLS_ENABLED=1` puis relancer Dash.
- Ne pas utiliser `dash.register_page()` — le routage est centralisé dans `src/dash_app/app.py` et déjà gaté par `DEVTOOLS_ENABLED`.
- Ne jamais modifier la sidebar/routing prod sans revue humaine explicite.

## Conventions Dash (obligatoires)

- Imports modernes: `from dash import html, dcc, dash_table` (jamais `dash_html_components`).
- Layout: conteneur `html.Div` cohérent; empty states en FR (ex: `dbc.Alert("Aucune donnée…", color="info")`).
- Ids stables pour les tests (ex: `id="forecasts-table"`).
- Styles sobres (Bootstrap / dbc); pas d’injection CSS lourde inline.

## Lecture de données (partitions)

Préférer les utilitaires existants. Exemple simple avec `src/tools/parquet_io.py`:

```python
from src.tools.parquet_io import latest_partition, read_parquet_latest

base = "data/forecast"
part = latest_partition(base)  # -> Path("data/forecast/dt=YYYYMMDD") ou None
if part:
    df = read_parquet_latest(base, filename="final.parquet")  # -> DataFrame ou None
else:
    df = None
```

Notes:
- Partitions journalières: `dt=YYYYMMDD`; partitions horaires: `dt=YYYYMMDDHH` (ex: `llm_summary`).
- Si df est None ou vide: afficher un empty state FR (jamais de crash).

## Tests — patrons validés

### Smoke des routes (dash.testing)

```python
import pytest
from dash.testing.application_runners import import_app

@pytest.mark.parametrize("route", [
    "/", "/dashboard", "/forecasts", "/regimes", "/risk",
    "/recession", "/agents", "/observability", "/news",
])
def test_routes_200(dash_duo, route):
    app = import_app("src.dash_app.app")
    dash_duo.start_server(app)
    dash_duo.driver.get(dash_duo.server_url + route)
    assert dash_duo.get_logs() == []
```

### LLM Summary (stub sûr)

Tester la vraie fonction: `src.agents.llm.arbiter_agent.run_llm_summary(save_base=...)`.

```python
import json
from pathlib import Path
from typing import List

def _fake_summary_json():
    return json.dumps({
        "asof": "2025-10-28T00:00:00Z",
        "regime": "neutral",
        "risk_level": "medium",
        "outlook_days_7": "modérément haussier",
        "outlook_days_30": "neutre",
        "key_drivers": ["cpi", "yield_curve"],
        "contributors": [
          {"source": "equity", "model": "baseline", "horizon": "7d", "symbol": "AAPL", "score": 0.7}
        ],
    })

def test_run_llm_summary_writes_partition(tmp_path, monkeypatch):
    from src.agents.llm import arbiter_agent
    class _DummyLLM:
        def generate(self, messages: List[dict], **kwargs) -> str:
            return _fake_summary_json()
    monkeypatch.setattr("src.agents.llm.runtime.LLMClient", lambda *a, **k: _DummyLLM())

    save_base = str(tmp_path / "data" / "llm_summary")
    summary = arbiter_agent.run_llm_summary(save_base=save_base)

    files = sorted((Path(save_base)).glob("dt=*/summary.json"))
    assert files, "no summary.json written"
    assert summary.asof
```

## Playwright / Navigateur (interactif + screenshots)

- 1re fois: `make ui-health-setup` (installe Chromium)
- Explorer interactivement: `npx playwright open http://127.0.0.1:8050`
- Générer des sélecteurs: `npx playwright codegen http://127.0.0.1:8050`
- Santé UI (toutes pages): `make ui-health` → JSON sous `data/reports/dt=.../` + PNG sous `artifacts/ui_health/`
- URL unique: `make snap-url URL=http://127.0.0.1:8050/forecasts OUT=artifacts/ui_health/forecasts.png`

## Hooks & CI (pré‑push)

- Activer les hooks: `make git-hooks`
- Le hook `.githooks/pre-push` rejette:
  - `dash_html_components` et `dash.register_page(` sous `src/dash_app/pages/`
  - un push si `make dash-smoke` ou `make ui-health` échoue
- Bypass exceptionnel: `SKIP_UI_CHECKS=1 git push`

## Commandes utiles

- Démarrer/Relancer Dash: `make dash-restart-bg` → http://127.0.0.1:8050
- Smoke HTTP: `make dash-smoke`
- UI Health + screenshots: `make ui-health`
- Artefacts ZIP (screenshots/logs): `make artifacts-zip`
- LLM Summary (one‑shot): `make llm-summary-run` (page Dash: `/llm_summary`)

## Documentation & PR

- Mettre à jour `docs/PROGRESS.md` (Delivered/Next/How‑to‑run) à chaque livraison.
- Utiliser `.github/pull_request_template.md` (checklist lint/tests/screenshots/docs)
- Joindre des captures récentes (artifacts/ui_health) et commandes exécutées (avec codes retour).

## Ce qu’il ne faut pas faire

- Dupliquer une page/agent existant (Quality/LLM/Macro, etc.).
- Modifier la nav/routing prod dans `src/dash_app/app.py` sans revue.
- Ajouter des placeholders en prod (si brouillon → page Integration DEV‑only).
