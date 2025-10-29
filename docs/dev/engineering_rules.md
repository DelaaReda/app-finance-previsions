# Règles de Développement — App Finance Prévisions (profondeur)

Objectif: éviter la dette, maximiser la réutilisation et garantir la stabilité (UI/agents/tests). Ces règles sont obligatoires pour tout dev junior/senior et s’appliquent aux PRs KILO.

## 1) Principes de base
- Réutilisation d’abord: chercher l’existant avant d’écrire (voir « 3) Trouver et réutiliser »).
- Zéro duplication d’agent/module/page. Si une variante est nécessaire, factoriser.
- UI = lecture/filtre/affichage. Pas de compute lourd, pas d’accès réseau.
- Données toujours via partitions immuables `data/<domaine>/dt=YYYYMMDD[HH]/…`.
- Empty states FR systématiques; jamais d’exception brute à l’écran.
- Sécurité: pas de secrets en repo; logs sobres.

## 2) Convention de fichiers et partitions
- Ecriture: agents écrivent sous `data/<domaine>/dt=YYYYMMDD/…` (ou horaire `YYYYMMDDHH`). Jamais d’écrasement.
- Lecture: helpers (ex. `src/tools/parquet_io.py`) ou loaders dédiés.
- Formats: Parquet/JSON. CSV seulement pour export UI.

## 3) Trouver et réutiliser l’existant (avant coder)
- Lister modules: `rg -n "^def |^class " src | less`
- Chercher un concept (ex. freshness): `rg -n "freshness|update-monitor" src`
- Regarder docs: `docs/architecture/*.md`, `docs/PROGRESS.md`, `docs/dev/*.md`.
- Vérifier pages: `src/dash_app/pages/*.py` (la plupart exposent un `layout()`).

## 4) UI Dash — règles
- Imports: `from dash import html, dcc, dash_table`; jamais `dash_html_components`.
- Pas de `dash.register_page()`: routage géré dans `src/dash_app/app.py`.
- Pages « Integration/DEV » uniquement sous `src/dash_app/pages/integration_<nom>.py`.
- Gating DEV: `DEVTOOLS_ENABLED=1` pour afficher ces pages. Ne pas exposer en prod.
- Layout: composant principal unique (Div/Card), ids stables, traductions FR.
- Données: lire dernières partitions avec loaders; fallback vide si absent.

## 5) Agents — règles
- Un agent = un rôle, idempotent, écrit une partition du jour/heure.
- Logging structuré (début/fin/volumétrie). Pas de `print()`.
- Entrées/sorties: fonctions pures autant que possible; I/O isolés.
- LLM: passer par `src/agents/llm/runtime.py` et schémas Pydantic (`schemas.py`).
- Orchestration: pas de boucles infinies; scheduler (APScheduler) et budgets d’étapes.

## 6) Tests — politique
- UI smoke (dash.testing): routes clés doivent rendre sans erreurs console.
- UI health (Playwright): screenshots + rapport JSON; vérifier éléments clés.
- Unitaires: tester helpers/IO/logic (ex. parquet_io, fusion, llm arbiter). Pas de réseau.
- Stub LLM: monkeypatch `src.agents.llm.runtime.LLMClient` pour JSON conforme `schemas.LLMEnsembleSummary`.

## 7) Hooks & CI
- Activer hooks: `make git-hooks`.
- pre-push rejette `dash_html_components` et `dash.register_page(` sous `src/dash_app/pages/` et lance `make dash-smoke` + `make ui-health`.
- Bypass exceptionnel: `SKIP_UI_CHECKS=1 git push` (ex: PR docs/tests uniquement).

## 8) Git & PRs
- Branches: `feature/<slug>`, `fix/<slug>`, `test/<slug>`.
- Commits conventionnels, petits (≤ ~400 lignes par PR). Ex: `feat(ui): add forecasts filters`.
- PR: décrire objectifs, fichiers touchés, commandes exécutées (codes retour), screenshots.
- Màj `docs/PROGRESS.md` (Delivered/Next/How‑to‑run) à chaque PR.

## 9) Observabilité
- Badge sidebar: vert si HTTP 200 + fraîcheur ≤ 25h; jaune si data stales; rouge si down.
- Pages Observability/Agents Status: lire freshness/partitions récentes; jamais de crash.

## 10) Anti‑patterns (interdits)
- Création de pages/prods sans gating DEV.
- Duplication de fonctions ou modules existants.
- Accès réseau dans l’UI.
- Exceptions brutes affichées; logs verbeux ou secrets.

## 11) Checklist avant PR
- `make dash-restart-bg` → manuel OK sur pages clés.
- `make dash-smoke` OK; `make ui-health` OK (screenshots présents).
- `pytest -q` OK (unitaires nouveaux/affectés).
- Docs à jour (PROGRESS + playbook si besoin).

## 12) Liens utiles
- Module index: `docs/dev/module_index.md`
- Playbook intégration (tests, patterns): `docs/dev/integration_playbook.md`

