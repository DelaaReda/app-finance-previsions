📣 PROMPT GÉNÉRAL DEV + Consignes Sprint 10 — App Finance Prévisions (Dash + Agents)

🎯 Vision & Principes
	•	Tu construis une usine d’agents qui ingèrent, contrôlent la qualité, prévoient (multi-horizons), agrègent et exposent leurs sorties dans une UI Dash pour un investisseur privé.
	•	Zéro duplication d’agent/module. Chaque agent écrit ses sorties en partitions datées : data/<domaine>/dt=YYYYMMDD/<fichier>.
	•	Historique ≥ 5 ans pour toute série utilisée en prévision.
	•	États vides en FR, jamais d’erreur “brute” à l’écran. JSON brut masqué (expander “Voir JSON”).
	•	Un seul point de vérité pour chemins/dossiers (via settings/env). Jamais de secrets en repo.

🧭 Repères & URLs
	•	Repo : https://github.com/DelaaReda/app-finance-previsions
	•	IDE web (Codespaces/Dev) : https://gloomy-superstition-5g7p5rvvqp5934gjx.github.dev
	•	UI Dash (local) : http://localhost:8050
	•	Routes clés : /dashboard, /signals, /portfolio, /regimes, /risk, /recession, /agents, /observability, /news
À ajouter/valider : /deep_dive, /forecasts, /backtests, /evaluation

🛠️ Environnement & Lancement

python -m venv .venv
source .venv/bin/activate     # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# Générer des données minimales
make equity-forecast && make forecast-aggregate
make macro-forecast && make update-monitor

# Démarrer / relancer Dash
make dash-start-bg     # ou: make dash-restart-bg
make dash-status && make dash-logs  # puis ouvrir http://localhost:8050

⚠️ data/ est ignoré par git. Si un fichier est tracké, le retirer (git rm --cached).

📁 Organisation du code
	•	UI Dash : src/dash_app/
	•	App & routing : src/dash_app/app.py
	•	Pages : src/dash_app/pages/*.py
(Dashboard, Signals, Portfolio, Regimes, Risk, Recession, AgentsStatus, Observability, News, Deep Dive, Forecasts, Backtests, Evaluation)
	•	Agents : src/agents/*.py → sorties sous data/**/dt=YYYYMMDD/...
	•	Ops/Tests : Makefile, tests/, ops/ui/mcp_dash_smoke.mjs

⸻

✅ Standards de code & qualité
	•	Typing obligatoire (fonctions publiques) + docstrings (Google/Numpy).
	•	Formatage/lint : Ruff (check + format) ; mypy (warn-only au début).
	•	pre-commit actif localement (voir `.pre-commit-config.yaml`).

Exécution rapide:
```bash
pip install pre-commit && pre-commit install
pre-commit run -a
```

pytest.ini

[pytest]
addopts = -q
testpaths = tests
filterwarnings =
    ignore::DeprecationWarning

mypy.ini

[mypy]
python_version = 3.11
ignore_missing_imports = True
warn_unused_ignores = True
warn_return_any = True

🔀 Git, branches, commits, PR
	•	Branches : s10/feat-<slug>, s10/fix-<slug>, s10/test-<slug>.
	•	Commits conventionnels + suivi sprint :
sprint-10 1/9 feat(quality): robust JSON parsing
sprint-10 2/9 fix(risk): NaN-safe VaR card
	•	PR atomique (≤ ~400 lignes). Rebase avant merge.

.github/PULL_REQUEST_TEMPLATE.md

## Objet
- [ ] Bugfix / [ ] Feature / [ ] Tests / [ ] Docs

## Résumé
_(ce que fait la PR et pourquoi)_

## Portée & risques
- Pages touchées: …
- Risques: …
- Rollback: …

## Check-list (DoD)
- [ ] pre‑commit OK
- [ ] CI verte (lint/type/tests)
- [ ] Tests unitaires ajoutés
- [ ] Smoke/E2E pertinents passent
- [ ] Empty states gérés
- [ ] Logs & erreurs utiles
- [ ] docs/PROGRESS.md mis à jour

Références:
- Process multi‑agents: `docs/dev/team-process.md`
- CODEOWNERS: `.github/CODEOWNERS`

⚙️ Config & environnements

.env.example

AFP_DATA_DIR=./data
DASH_ENV=dev

Un seul point de vérité pour les chemins via settings.DATA_DIR (lit AFP_DATA_DIR).

🧾 Chargement & validation des données

src/dash_app/data/schema.py

def ensure_cols(df, required: list[str]) -> bool:
    return not df.empty and set(required) <= set(df.columns)

def null_ratio(df, col: str) -> float:
    return float(df[col].isna().mean()) if col in df else 1.0

Usage (ex. evaluation.py)

from ..data.schema import ensure_cols
if not ensure_cols(df, ["model","horizon","mape"]):
    logger.warning("Eval: colonnes manquantes => %s", df.columns.tolist())

⚡ Dash — patterns & performance
	•	Callbacks courts + memoization I/O :

from functools import lru_cache
@lru_cache(maxsize=32)
def load_forecasts_cached() -> pd.DataFrame:
    return read_parquet(p_forecasts)

	•	State partagé : dcc.Store (évite relectures).
	•	DataTable volumineux → virtualization=True, page_size=25.
	•	Empty states systématiques (figure {} si vide).
	•	Heavy compute en amont (agents), UI = lecture/filtre/affichage.

🧑‍🎨 UI/UX & accessibilité
	•	Titres H1/H3 cohérents ; labels FR.
	•	Filtres synchronisés (date, multi-tickers/horizons).
	•	Navigation stable (sidebar + URL) ; focus clavier OK.

🧩 Checklists d’implémentation

➕ Ajouter / modifier une PAGE Dash
	1.	Créer src/dash_app/pages/xxx.py (layout + callbacks).
	2.	Enregistrer la route dans src/dash_app/app.py (sidebar + dcc.Location).
	3.	Charger la dernière partition (util utils/partitions.py) :
	•	latest_dt("data/forecast") ⇒ YYYYMMDD
	•	read_parquet_latest("data/forecast", "final.parquet")
	4.	UI : DataTable/Graph Plotly, filtres (ticker/horizon/date), état vide FR.
	5.	Tests :
	•	Manuel : http://localhost:8050/xxx
	•	Smoke inclus (route surveillée)
	•	MCP/Playwright sans erreur bloquante

🤖 Ajouter / modifier un AGENT
	1.	src/agents/<nom>_agent.py
	•	Entrées : parquet/json existants (prix, forecasts)
	•	Sortie datée : data/<domaine>/dt=YYYYMMDD/<nom>.parquet|json
	•	logging début/fin/volumes/anomalies (pas de print())
	2.	Makefile : cible dédiée
PYTHONPATH=src python -m src.agents.<nom>_agent
	3.	Idempotent : n’écrit que dt=today.
	4.	Qualité : trous/duplicats → rapport (ex. data/quality/dt=.../freshness.json).
	5.	Validation : exécuter la cible, vérifier sorties, brancher la page correspondante.

⸻

🧪 Tests — Manuel, Smoke, MCP/Playwright, Unitaires & E2E

A) Manuel (avant chaque push)
	•	make dash-restart-bg, vérifier les routes clés (HTTP 200 + rendu).
	•	Badge statut global (sidebar) :
	•	🟢 200 + fraîcheur ≤ 25h
	•	🟡 200 mais données anciennes
	•	🔴 serveur down

B) Smoke (automatisé)

make dash-smoke   # vérifie HTTP 200 sur routes connues

C) MCP (évaluation UX automatisée)

make dash-mcp-test
# Script Node ops/ui/mcp_dash_smoke.mjs : rapport + stderr
# Si TypeError "file must be string": corriger artefacts/screenshot paths

D) Playwright — screenshot obligatoire avant commit UI

make ui-health-setup   # 1ère fois (installe Chromium)
make ui-health         # génère data/reports/dt=YYYYMMDD/ui_health_report.json
                       # + artifacts/ui_health/*.png
# Page unique (ex. legacy Streamlit):
make snap-url URL=http://127.0.0.1:5556 OUT=artifacts/ui_health/forecast_5556.png

Critères : pas d’alertes/erreurs visibles ; composants clés présents ; joindre/référencer screenshot en PR.

E) Unitaires & callbacks Dash
	•	pytest -q (logique pure, pas d’I/O disque).
	•	dash.testing : présence de composants clés (Graph/DataTable) et callbacks basiques.

tests/conftest.py

import os, pytest
@pytest.fixture(autouse=True)
def set_data_dir(tmp_path, monkeypatch):
    d = tmp_path / "data"; d.mkdir()
    monkeypatch.setenv("AFP_DATA_DIR", str(d))
    yield


⸻

🧰 Make & CI (raccourcis)

lint:
\tpre-commit run -a
typecheck:
\tmypy src
qa:
\tmake lint && make typecheck && pytest -q

E2E headless : timeouts 6–10s, assertions souples (stabilité CI).

⸻

🔎 Observabilité & logs

src/dash_app/logging_setup.py

import logging, sys
def setup_logging():
    h = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO); h.setFormatter(fmt); root.handlers[:] = [h]

	•	Appeler setup_logging() au démarrage.
	•	Page Observability : lit freshness.json, affiche journaux (tail), statut agents.

⸻

🧯 Dépannage rapide (FAQ)
	•	Port 8050 occupé : make dash-stop puis make dash-start-bg
	•	Manque numpy/requests : activer .venv + pip install -r requirements.txt
	•	Pas de final.parquet : make equity-forecast && make forecast-aggregate
	•	Badge global 🟡 : make update-monitor (fraîcheur > 25h)
	•	MCP “file undefined” : corriger noms/chemins dans ops/ui/mcp_dash_smoke.mjs, relire stderr
	•	UI pas à jour : make dash-restart-bg + make dash-status + make dash-logs

⸻

🔐 Sécurité & conformité
	•	Aucune PII en logs/écrans de démo.
	•	.env non versionné ; secret-scan via pre-commit hook.
	•	Documenter licences & sources dans docs/DATA_SOURCES.md.

⸻

🗂️ Sprint 10 — Objectifs & Tâches prioritaires

Objectif : rétablir la cohérence fonctionnelle/visuelle Dash, corriger bugs critiques, réintégrer fonctionnalités Streamlit manquantes, afficher toutes les données disponibles (Parquet), assurer fraîcheur/intégrité (freshness.json) et couvrir par tests (unitaires + E2E).

Top 9 :
	1.	[Bug] Quality — corriger AttributeError: 'str' object has no attribute get ; affichage indicateurs OK.
	2.	[Bug] Backtests & Évaluation — pages vides → afficher scores & KPIs.
	3.	[Bug] Risk & Regimes — ré-alimenter depuis sources (mesures de risque, segmentation).
	4.	[Feature] Parité Streamlit — multi-actifs Deep Dive, comparaisons globales, filtres historiques.
	5.	[Feature] Observability — fraîcheur (freshness.json) + journaux.
	6.	[Feature] Agents Status — états (actif/erreur/progression).
	7.	[Test] E2E UI — parcours critiques (Forecasts, Deep Dive, …).
	8.	[Test] Unit callbacks — logique de transformation + rendu composants.
	9.	[Test] Fraîcheur données — test auto freshness.json + existence Parquet.

Critères d’acceptation (par ticket)
	•	Pas d’erreur console, empty state géré, 1+ graph & 1+ tableau (si pertinent), filtres OK, logs utiles, tests ajoutés (unit + E2E), docs PROGRESS.md mises à jour.

⸻

✍️ Commits & Documentation
	•	Conventional Commits + progression sprint en tête :
	•	sprint-10 3/9 feat(ui): add forecasts page with filters
	•	sprint-10 4/9 fix(agents): handle missing final.parquet gracefully
	•	sprint-10 5/9 chore(ops): improve dash-smoke
	•	Docs :
	•	Mettre à jour docs/PROGRESS.md (Delivered / In progress / Next + “Comment valider” = URLs + commandes).
	•	docs/architecture/dash_overview.md pour toute nouvelle page/agent (I/O + fichiers lus/écrits).

⸻

✅ Definition of Done (DoD)
	•	Fonction réellement implémentée et accessible via URL locale.
	•	Smoke OK (make dash-smoke) + MCP OK (sans erreur bloquante).
	•	Playwright exécuté, screenshots générés & vérifiés.
	•	Observability vert et partitions du jour présentes.
	•	Docs à jour (PROGRESS + dash_overview).
	•	Commits propres, atomiques, conventionnels.

⸻

Si tu veux, je peux te générer un squelette de page (par ex. pages/quality.py) ou un agent type avec lecture/écriture partitionnée + tests unitaires minimalistes.
## UI React — Consignes Dev

- Démarrer l'API Dash/Flask: `make dash-restart-bg` (health: `GET /api/health`).
- Démarrer le front React: `make react-dev` → http://127.0.0.1:5173 (proxy `/api`).
- Endpoints disponibles (extrait): `/api/forecasts`, `/api/news`, `/api/watchlist`, `/api/settings`, `/api/llm/judge/run`.
- Observabilité: `make dash-fore` (console), `make dash-logs`, `make ui-otel-follow` (si Docker).
- Ajout d'une page React: créer `webapp/src/pages/NomPage.tsx` + router dans `App.tsx`. Utiliser `src/api/client.ts`.
