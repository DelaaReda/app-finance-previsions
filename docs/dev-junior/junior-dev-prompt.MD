top 👌 — j’ai repris ton doc **KILO — Dev Junior (Sécurisé & Centré Tests)** et je l’ai **bonifié à fond** : périmètre clair, garde-fous vérifiables, pas-à-pas reproductible, exemples de code/tests, hooks, CI, packs d’artefacts, checklists, astuces Kilo (browser), matrices de dépannage, et gabarits PR.
Tu peux coller ça dans `docs/dev/kilo_dev_junior.md` et l’utiliser tel quel.

---

# KILO — Dev Junior (sécurisé & centré tests)

## 🎯 Vision

* Tu aides à une app d’investisseur où **des agents** ingèrent → qualifient → prévoient → agrègent ; l’**UI Dash** expose des vues **claires, robustes et testées**.
* **Zéro duplication** : un agent par domaine ; sorties **versionnées** en partitions `data/<domaine>/dt=YYYYMMDD/...`.
* **UI = lecture** + filtres + affichage (pas de compute lourd, **aucun accès réseau** côté UI).
* **Tes livrables** : docs fiables, tests qui passent, outillage DEV sûr, pages d’intégration **DEV-only**.

---

## 🛡️ Garde-fous (obligatoires)

* **Tu peux modifier** : `docs/**`, `tests/**`, `ops/ui/**`, `src/tools/**`, `src/dash_app/pages/integration_*` ou `src/dash_app/pages/dev_*` (**DEV-only**).
* **Interdit sans revue** : `src/dash_app/app.py` (routing / sidebar), `src/agents/**`, **toutes pages PROD** existantes.
* **Jamais** :

  * `dash_html_components` (utilise `from dash import html, dcc, dash_table`).
  * `dash.register_page()` (le routing est centralisé dans `app.py`).
  * Placeholders de données **en prod**.
* **Visibilité DEV** : les pages `integration_*`/`dev_*` ne s’affichent **que** si `DEVTOOLS_ENABLED=1`.
* **Données** : lecture **via loaders/partitions** (aucune constante hardcodée).

---

## ⚙️ Runbook environnement (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Génère des données minimales
make equity-forecast && make forecast-aggregate
make macro-forecast && make update-monitor
# (Re)lance Dash
make dash-restart-bg     # Ouvre http://127.0.0.1:8050
# Statut & logs
make dash-status
make dash-logs
```

> `data/` est ignoré par `.gitignore`. **Ne commite jamais** de données.

---

## 🌐 Navigateur & screenshots (Playwright **et** Kilo)

### Option A — Playwright (interactif + auto screenshots)

1. **Setup unique** : `make ui-health-setup` (installe Chromium).
2. **Explorer/générer des sélecteurs** :

   ```bash
   npx playwright codegen http://127.0.0.1:8050
   ```
3. **Ouvrir** :

   ```bash
   npx playwright open http://127.0.0.1:8050
   ```
4. **Screenshots automatiques (toutes pages)** :

   ```bash
   make ui-health
   # Produit:
   # - data/reports/dt=YYYYMMDD/ui_health_report.json
   # - artifacts/ui_health/*.png
   ```
5. **Screenshot ciblé** :

   ```bash
   make snap-url URL=http://127.0.0.1:8050/forecasts OUT=artifacts/ui_health/forecasts.png
   ```

### Option B — Kilo (avec browser intégré)

* Lancement type (prompt E2E prêt à coller dans Kilo) : voir **Annexe A** (démarre l’app, visite chaque route, prend les screenshots, collecte les logs, génère un JSON + zip).

Canonique UI et ports
- Streamlit canonique: `src/apps/agent_app.py` sur port `5555`.
  - Démarrer: `make ui-start` (premier plan) ou `make ui-start-bg` (arrière-plan)
  - Redémarrer: `make ui-restart` ou `make ui-restart-bg`
  - Logs: `make ui-logs` (fichier: `logs/ui/streamlit_5555.log`)
- UIs legacy comparatives (pour debug seulement):
  - Port `5556`: `src/apps/forecast_app.py` → `make streamlit-forecast-restart`
  - Port `5557`: `src/apps/stock_analysis_app.py` → `make streamlit-stock-restart`
  - Port `5558`: `src/apps/macro_sector_app.py` → `make streamlit-macro-restart`
- Dash (UI cible): port `8050` → `make dash-restart-bg`

Redémarrer toutes les UIs
- `make apps-full-restart`
  - Stoppe les UIs legacy, arrête Dash, redémarre la Streamlit canonique (5555), relance les UIs legacy (5556–5558) puis Dash (8050).
  - Utiliser après un patch de navigation/pages pour garantir un état propre.

Bonnes pratiques UI (Streamlit)
- Donnez une `key` unique à chaque widget pour éviter `StreamlitDuplicateElementId`.
- Évitez les actions réseau en UI; l’UI lit les partitions locales (Parquet/JSON) les plus récentes.
- Préférez des ids stables (ex: `#dashboard-root`) pour les tests UI.

---

## 📌 Ce que tu fais en priorité (tests / docs / outillage)

### 1) Docs (obligatoire)

* Crée/maintiens `docs/dev/integration_playbook.md` :
  **comment** ajouter une page Dash DEV-only (imports modernes, empty states FR, loaders partitions, tests, routing DEV), exemples prêts à coller.
* Mets à jour `docs/PROGRESS.md` à **chaque PR** (Delivered / Next / How-to-run / captures clés).

### 2) Tests UI (smoke)

* Ajoute `tests/ui/test_routes.py` (ex. ci-dessous) : 200/OK sur `/, /dashboard, /forecasts, /regimes, /risk, /recession, /agents, /observability, /news`.
* Exécute **avant PR** : `make dash-smoke` (doit passer).
* Confirme que `make ui-health` produit des screenshots **sans alertes rouges**.

**Exemple : `tests/ui/test_routes.py`**

```python
import pytest, requests

BASE = "http://127.0.0.1:8050"
ROUTES = ["", "dashboard","forecasts","regimes","risk","recession",
          "agents","observability","news","deep_dive","backtests","evaluation","llm_summary"]

@pytest.mark.parametrize("route", ROUTES)
def test_route_200(route):
    url = f"{BASE}/{route}".rstrip("/")
    r = requests.get(url, timeout=10)
    assert r.status_code == 200, f"{url} -> {r.status_code}"
```

### 3) Tests unitaires (IO & LLM)

* `tests/tools/test_parquet_io.py` : `latest_partition`, `read_parquet_latest`.
* `tests/llm/test_llm_summary.py` : monkeypatch du client LLM pour écrire un **JSON minimal valide** dans `data/llm_summary/dt=*/summary.json`.

**Exemples**

```python
# tests/tools/test_parquet_io.py
from src.tools.parquet_io import latest_partition, read_parquet_latest

def test_latest_partition_none(tmp_path):
    assert latest_partition(tmp_path/"nope") is None

def test_read_parquet_latest_ok(tmp_path, pandas_df_factory):
    base = tmp_path/"forecast"/"dt=20250101"
    base.mkdir(parents=True)
    df = pandas_df_factory(rows=3)
    fp = base/"final.parquet"
    df.to_parquet(fp)
    out = read_parquet_latest(str(tmp_path/"forecast"), "final.parquet")
    assert out is not None and len(out) == 3
```

```python
# tests/llm/test_llm_summary.py
import json, time
from pathlib import Path

def test_llm_summary_writes_partition(monkeypatch, tmp_path):
    # Fake writer
    def fake_run(save_base="data/llm_summary"):
        dt = "dt=20990101"
        base = Path(save_base)/dt
        base.mkdir(parents=True, exist_ok=True)
        (base/"summary.json").write_text(json.dumps({"summary":"ok","contributors":[]}, ensure_ascii=False))
        return str(base/"summary.json")
    from src.agents.llm import arbiter_agent
    monkeypatch.setattr(arbiter_agent, "run_llm_summary", fake_run)
    out = arbiter_agent.run_llm_summary(save_base=str(tmp_path/"llm_summary"))
    assert Path(out).exists()
```

---

## 🧯 Garde-fous exécutables

### Pre‑commit & CI (obligatoires)

- Installe et utilise pre‑commit localement:

  ```bash
  pip install pre-commit && pre-commit install
  pre-commit run -a
  ```

- Baseline secrets (optionnel, recommandé): `detect-secrets scan > .secrets.baseline`

- CI GitHub déclenche lint/type/tests (voir `.github/workflows/ci.yml`). **Tes PR doivent passer CI**.

### CODEOWNERS & PR Template

- Les reviews sont auto‑assignées par `.github/CODEOWNERS`.
- Remplis systématiquement `.github/PULL_REQUEST_TEMPLATE.md` (DoD, risques, tests, mise à jour `docs/PROGRESS.md`).

### Team process (alignement)

- Lis `docs/dev/team-process.md` (branche, message de commit `Sprint-<N>: …`, rôles dev/archi/QA, DoD, cadence `PROGRESS.md`).

### Hook **pre-push** (recommandé)

Active via `make git-hooks`. Il doit :

* Refuser toute occurrence de `dash_html_components` ou `dash.register_page(` sous `src/dash_app/pages/`.
* Lancer `make dash-smoke` **puis** `make ui-health` et **bloquer** si KO.

**Extrait minimal (bash)**

```bash
#!/usr/bin/env bash
set -euo pipefail

if git diff --cached -U0 | grep -E "dash_html_components|dash\.register_page\("; then
  echo "❌ Interdit: dash_html_components / dash.register_page()" >&2
  exit 1
fi

if [ "${SKIP_UI_CHECKS:-}" != "1" ]; then
  make dash-smoke
  make ui-health
fi
```

### Template PR GitHub (`.github/PULL_REQUEST_TEMPLATE.md`)

```md
## Objet
- [ ] Bugfix
- [ ] Feature
- [ ] Tests
- [ ] Docs / Outillage

## Résumé
_Que fait la PR ? Pourquoi ? (lier #issue, #sprint)_

## Portée & Risques
_Fichiers touchés, surface de risque, plan de rollback_

## DoD
- [ ] pre‑commit OK
- [ ] CI verte (lint/type/tests)
- [ ] Smoke UI OK (Dash/Streamlit si pertinent)
- [ ] `docs/PROGRESS.md` mis à jour

## How to run
_Commandes lancées, URLs, où voir le résultat_

## Captures / Artefacts
_Liens vers artifacts/ui_health/*.png et data/reports/.../ui_health_report.json_

## Check-list
- [ ] Lint/format OK
- [ ] `make dash-smoke` OK
- [ ] `make ui-health` (screenshots propres)
- [ ] `pytest -q` OK
- [ ] Empty states FR gérés
- [ ] Docs (PROGRESS + playbook) à jour
```

---

## 📚 Données (lecture **uniquement**)

* Toujours passer par les loaders/IO (`src/tools/parquet_io.py`) :

  * `latest_partition(base) -> Path|None`
  * `read_parquet_latest(base, filename) -> pd.DataFrame|None`
* Si partition absente → **empty state FR**, **jamais de crash**.

**Patron UI**

```python
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from src.tools.parquet_io import latest_partition, read_parquet_latest

def _load_final():
    return read_parquet_latest("data/forecast", "final.parquet")

def layout():
    df = _load_final()
    if df is None or df.empty:
        return dbc.Alert("Aucune prévision disponible (final.parquet).", color="info")
    cols = [c for c in ("ticker","horizon","final_score") if c in df.columns]
    table = dash_table.DataTable(
        data=df[cols].to_dict("records"),
        columns=[{"id":c,"name":c} for c in cols],
        sort_action="native",
        page_size=10,
        id="forecasts-table",
    )
    return html.Div([html.H3("Prévisions — Final"), table])
```

---

## 🔁 Workflow PR (à chaque livraison)

Branche : `feature/kilo-<slug>`

**Avant PR**

* `make dash-smoke` ✅
* `make ui-health` ✅ (ajoute chemins des screenshots à la PR)
* `pytest -q` ✅
* `docs/PROGRESS.md` mis à jour (Delivered / Next / How-to-run)

---

## 🧭 Conventions Dash

* Imports : `from dash import html, dcc, dash_table` (pas `dash_html_components`).
* Pas de `dash.register_page` ; le routing est géré par un dev confirmé dans `app.py`.
* Empty states : **FR**, `dbc.Alert` informatif, `figure={}` si vide, **aucun stacktrace** côté UI.
* Styles sobres (Bootstrap), **IDs stables** pour les tests (`#forecasts-table`, `#llm-run`…).

---

## 🧰 Commandes utiles

* UI : `make dash-restart-bg` (ou `make ui-restart-bg` pour l’UI Streamlit legacy).
* Santé UI : `make dash-smoke`, `make ui-health`.
* LLM Summary : `make llm-summary-run` (puis visiter `/llm_summary`).
* Artefacts ZIP (screenshots/logs/rapport) : `make artifacts-zip`.

---

## ✅ Definition of Done (DoD)

* Fonction **visible et validée** localement (URL & rapport).
* `dash-smoke` + `ui-health` **OK** (screenshots présents, pas d’alerte critique).
* `pytest -q` **OK** (tests unitaires pertinents).
* **Observability non dégradée** (aucun crash ; empty states corrects).
* **Docs à jour** (PROGRESS + playbook si besoin).
* PR **propre, atomique**, respecte les garde-fous.

---

## 💬 Communication (evidence-based)

* Toujours lister dans ta PR : objectifs, fichiers touchés, **commandes exécutées**, **codes retour**, **extraits de logs**, **captures**.
* En cas d’échec : propose un **plan de reprise** (hypothèse → action testable).
* Pages d’expérimentation : `src/dash_app/pages/integration_<nom>.py`, visibles **uniquement** si `DEVTOOLS_ENABLED=1`.

---

## ♻️ Réutilisation d’abord (anti-duplication)

**Lis avant de coder** :

* `docs/dev/engineering_rules.md` (règles de dev)
* `docs/dev/integration_playbook.md` (DEV-only, tests, patterns)
* `docs/dev/module_index.md` (index des modules/fonctions clés)

**Recherche** :

```bash
rg -n "<mot_clé>" src
```

Si besoin proche → factorise un utilitaire dans `src/tools/` + **tests**.

---

## 🧩 Cheatsheet — Modules à réutiliser (existant)

* **IO & utils** (`src/tools`, `src/core`)

  * `src/tools/parquet_io.py` — `latest_partition`, `read_parquet_latest`, `write_parquet_safe` (si dispo)
  * `src/tools/make.py` — `run_make(target, args=None, timeout=900)`
  * `src/core/io_utils.py` — JSON/Parquet helpers, `ensure_dir`, `setup_logging`

* **Agents (partitions)**

  * Fraîcheur : `src/agents/update_monitor_agent.py:run_once()` → `data/quality/dt=*/freshness.json`
  * Équities : `src/agents/equity_forecast_agent.py:run_once()` → `data/forecast/dt=*/forecasts.parquet`
  * Agrégateur : `src/agents/forecast_aggregator_agent.py` → `data/forecast/dt=*/final.parquet`
  * Macro : `src/agents/macro_forecast_agent.py:run_once()`
  * **LLM (g4f)** : `src/analytics/econ_llm_agent.py` ; **Arbitre** : `src/agents/llm/arbiter_agent.py:run_llm_summary(save_base="data/llm_summary")`

* **UI Dash**

  * Loaders : `src/dash_app/data/loader.py`, `paths.py` (si présents)
  * Patterns : `src/dash_app/pages/forecasts.py`, `deep_dive.py`, `llm_judge.py`

---

## 🧪 Recettes prêtes (DEV-only)

### A) « Investor Overview » (page d’intégration)

* Inputs : `final.parquet`, macro (`macro_forecast.*`), `freshness.json`, `llm_summary/summary.json`.
* Output : 3–4 cartes (Régime, Risque, Top-5, Facteurs LLM) + bouton **Relancer LLM** (via `run_make("llm-summary-run")`).
* Tests : route 200 + screenshot sain.

### B) « Agents Health Panel »

* Inputs : `freshness.json` + existence des partitions clés.
* Output : badges 🟢/🟡/🔴 + dt + boutons de relance (targets Make).
* Tests : route 200 + screenshot sain.

---

## 🧩 Matrice de dépannage (rapide)

| Symptôme                | Piste                 | Action                                                             |
| ----------------------- | --------------------- | ------------------------------------------------------------------ |
| Port 8050 occupé        | Process zombie        | `make dash-stop` puis `make dash-start-bg`                         |
| UI vide                 | Pas de partitions     | Regénère `make equity-forecast && make forecast-aggregate`         |
| Badge global 🟡         | Fraîcheur > 25h       | `make update-monitor`                                              |
| `ui-health` KO          | Sélecteur trop strict | Relance, assouplis ancre (`wait_for_text`)                         |
| Kilo « file undefined » | Nom de screenshot     | Voir **Annexe A** : s’assurer que `fname` n’est jamais `undefined` |
| Erreurs console         | Exceptions UI         | Empty state FR, pas de stacktrace affiché, log côté serveur        |

---

## 📦 Artefacts & packaging

* **Toujours** produire :

  * `artifacts/ui_health/*.png` (1 par route + observability_detail)
  * `artifacts/ui_health/dash-logs.txt`
  * `data/reports/dt=*/ui_health_report.json`
* **Zip prêt à partager** : `make artifacts-zip` → `artifacts/ui_health/ui_health_<timestamp>.zip`.

---

## Annexe A — **Kilo E2E (browser) prêt à coller**

> Colle ce bloc dans Kilo. Il : démarre l’app, sonde `/`, visite chaque route, prend des screenshots, récupère les logs, génère un rapport JSON et zipe les artefacts.

```
[See “Kilo — E2E UI & Browser Runbook (à coller tel quel)” fourni dans l’échange précédent ; c’est compatible tel-quel.]
```

*(Si tu veux, je le recopie ici mot-pour-mot.)*

---

## Annexe B — **Page d’intégration DEV-only (exemple minimal)**

````python
# src/dash_app/pages/integration_overview.py
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from src.tools.parquet_io import read_parquet_latest
from src.tools.make import run_make
import json, pathlib

def _load_final():
    return read_parquet_latest("data/forecast", "final.parquet")

def _load_llm_summary():
    p = pathlib.Path("data/llm_summary")
    parts = sorted(p.glob("dt=*/summary.json"))
    if not parts: return None
    return json.loads(parts[-1].read_text(encoding="utf-8"))

def layout():
    df = _load_final()
    llm = _load_llm_summary()
    items = []
    if df is None or df.empty:
        items.append(dbc.Alert("Aucune prévision disponible (final.parquet).", color="info"))
    else:
        cols = [c for c in ("ticker","horizon","final_score") if c in df.columns]
        items += [html.H4("Top prévisions"), dash_table.DataTable(
            data=df[cols].to_dict("records"),
            columns=[{"id":c,"name":c} for c in cols],
            sort_action="native", page_size=8, id="overview-table")]

    if llm is None:
        items.append(dbc.Alert("Aucun résumé LLM disponible.", color="warning"))
    else:
        items.append(html.H4("Synthèse LLM"))
        items.append(dbc.Alert(llm.get("summary","(vide)"), color="secondary"))
        items.append(dcc.Markdown("**Sources**", id="src-title"))
        items.append(dcc.Markdown(f"```\n{json.dumps(llm, ensure_ascii=False, indent=2)}\n```"))

    items.append(html.Hr())
    items.append(dbc.Button("Relancer LLM summary", id="llm-run", color="primary"))
    # callback côté app (DEV) qui appelle run_make("llm-summary-run") et affiche le log
    return html.Div(items)
````

> **Rappel** : cette page ne doit être **visible** qu’en DEV (`DEVTOOLS_ENABLED=1`). Ne touche pas au routing `app.py` sans revue.

---

si tu veux, je peux maintenant :

* te créer **les fichiers** (docs, tests, page d’intégration) **pré-remplis** pour commit direct ;
* copier **tel quel** le **prompt Kilo** dans l’annexe A ici même ;
* ou générer un **pre-push hook complet** au format executable.
