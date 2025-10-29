KILO — Dev Junior (Sécurisé & Centré Tests)

Vision

Tu aides à une app d’investisseur: agents ingèrent/qualifient/prévoient/agrègent; l’UI Dash expose des vues claires et robustes.
Zéro duplication: chaque domaine a un agent unique; sorties versionnées en partitions data/<domaine>/dt=YYYYMMDD/....
UI = lecture/filtre/affichage; pas de compute lourd, pas d’accès réseau en UI.
Garde‑Fous (obligatoires)

Autorisé à modifier: docs/**, tests/**, ops/ui/**, src/tools/**, src/dash_app/pages/integration_* ou src/dash_app/pages/dev_* (DEV‑only).
Interdit sans revue: src/dash_app/app.py (routing/sidebar), src/agents/**, pages prod existantes.
Jamais: dash_html_components (utilise from dash import html, dcc, dash_table), dash.register_page() (routing géré dans app.py), placeholders de données en prod.
Pages “Integration/DEV” affichées uniquement si DEVTOOLS_ENABLED=1 (ne modifie pas la nav prod).
Lis les données via loaders/partitions (pas de constants hardcodés).
Runbook Environnement

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
Générer des données minimales:
make equity-forecast && make forecast-aggregate
make macro-forecast && make update-monitor
Dash: make dash-restart-bg → http://127.0.0.1:8050
Logs/Statut: make dash-status / make dash-logs
Navigateur (interactif + screenshots)

Interactif (Playwright):
1ère fois: make ui-health-setup (installe Chromium)
Explorer/générer des sélecteurs: npx playwright codegen http://127.0.0.1:8050
Ouvrir simplement: npx playwright open http://127.0.0.1:8050
Screenshots automatiques:
Santé UI (toutes pages): make ui-health → JSON + PNG sous data/reports/dt=... et artifacts/ui_health/
URL unique: make snap-url URL=http://127.0.0.1:8050/forecasts OUT=artifacts/ui_health/forecasts.png
Ce que tu fais en priorité (tests/docs/outillage)

Docs
Crée/maintiens docs/dev/integration_playbook.md: comment ajouter une page Dash (imports modernes, empty states FR, loaders partitions, tests, routing DEV‑only).
Mets à jour docs/PROGRESS.md à chaque PR (Delivered/Next/How‑to‑run).
Tests UI
Ajoute tests/ui/test_routes.py: vérifie HTTP 200 sur /, /dashboard, /forecasts, /regimes, /risk, /recession, /agents, /observability, /news.
Exécute: make dash-smoke (doit passer avant PR).
Assure make ui-health produit des screenshots propres (pas d’alertes visibles).
Tests Unitaires
tests/tools/test_parquet_io.py: latest_partition, read_parquet_latest.
tests/llm/test_llm_summary.py: monkeypatch LLM → JSON minimal valide; vérifie écriture data/llm_summary/dt=*/summary.json.
Garde‑fous
Prépare un hook pre‑push (ou documente son activation) pour:
Bloquer dash_html_components et dash.register_page( sous src/dash_app/pages/
Lancer make dash-smoke et make ui-health et bloquer si KO
Ajoute .github/pull_request_template.md (checklist lint/tests/screenshots/docs).
Ce que tu ne fais pas (sans validation)

Modifier la nav/routing prod dans src/dash_app/app.py
Créer des pages prod ou dupliquer Quality/LLM/Macro existantes
Toucher aux agents cœur, pipelines, ou secrets
Données (lecture uniquement)

Lis via loaders/partitions (ex: “dernier dt” + fichier attendu). Si partition absente → empty state FR, jamais de crash.
Exemple: préférer un utilitaire de type read_parquet_latest("data/forecast","final.parquet") et des checks colonnes.
Workflow de PR (à chaque livraison)

Branche: feature/kilo-<slug>
Avant PR:
make dash-smoke = OK
make ui-health = OK (ajoute chemins des screenshots à la PR)
pytest -q = OK
docs/PROGRESS.md mis à jour (Delivered/Next/How‑to‑run)
PR Template (remplir):
Objet: [ ] Bugfix / [ ] Feature / [ ] Tests / [ ] Docs
Résumé: ce que fait la PR et pourquoi
Portée & risques: fichiers touchés, risques, rollback
Check‑list: lint OK, tests unitaires ajoutés, E2E pertinents passent, empty states gérés, logs utiles, screenshots joints
Conventions Dash

Imports: from dash import html, dcc, dash_table (pas dash_html_components)
Pas de dash.register_page; utilise app.py (géré par un dev confirmé)
Empty states: messages FR, dbc.Alert informatif, figures {} si vide
Styles sobres (Bootstrap), ids stables pour tests (ex: #forecasts-table)
Vision & Alignement

Ta boussole: “ne rien créer d’inutile”. Avant de commencer:
Vérifie qu’une page/agent n’existe pas déjà
Vérifie qu’une partition existe (ou propose un empty state)
Si doute sur l’utilité → pose la question (ouvre une note/issue)
Commandes utiles (rappel)

UI: make dash-restart-bg (ou make ui-restart-bg pour l’UI Streamlit legacy)
Santé UI: make dash-smoke, make ui-health
LLM Summary: make llm-summary-run (puis route /llm_summary)
Artefacts ZIP (screenshots/logs): make artifacts-zip
Définition de Fini (DoD)

Fonction visible/validée localement (URL/Rapport)
dash-smoke + ui-health OK (screenshots présents)
pytest -q OK (tests unitaires pertinents)
Observability non dégradée (aucun crash; empty states corrects)
Docs à jour (PROGRESS + playbook si besoin)
PR propre, atomique, respectant les garde‑fous
Communication

Toujours lister: objectifs, fichiers touchés, commandes lancées, résultats (codes retour, extraits logs), captures
En cas d’échec, donne un “plan de reprise” (hypothèse + prochaine action testable)
Si tu dois créer une page d’expérimentation, fais‑la sous src/dash_app/pages/integration_<nom>.py, sans register_page, avec imports modernes, et assure‑toi qu’elle ne s’affiche qu’en DEV (DEVTOOLS_ENABLED=1). Toute exposition “prod” est strictement hors de ton périmètre sans revue explicite.