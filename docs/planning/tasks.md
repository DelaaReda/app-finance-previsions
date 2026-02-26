# Tasks détaillées orientées exécution par agents codex (OpenClaw)

## Gate Status (source of truth)
- `BATCH-01`: `PASS` (QA signoff already present)
  - artifact: `finance-app/openclaw-gates/batch-01-20260225-000127.md`
  - keys: `QA_SIGNOFF: YES`, `VERDICT: PASS`, `BLOCKER_ID: NONE`
- `BATCH-02`: `PASS` (QA signoff now present)
  - artifact: `finance-app/openclaw-gates/batch-02-20260225-202042.md`
  - keys: `QA_SIGNOFF: YES`, `VERDICT: PASS`, `BLOCKER_ID: NONE`
- If a runtime role output reports `QA_PASS_SIGNATURE_UNVERIFIED`, re-check the artifact above before keeping the blocker.

## Convention de dispatch
- **Rôles (core chain)**: planner, dev, tester, qa
- **Taille cible**: 2-4h / tâche
- **Format sortie obligatoire (contrat)**: STATUS / DELTA / EVIDENCE / RISKS / NEXT / VERDICT / BLOCKER_ID / NEXT_ACTION_UNIQUE
- **EVIDENCE**: suivre `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md` (kv `key=value;...`)

## Architecture d'intégration détaillée (anti-chevauchement, sans nouvelles tâches)
- Cette section n'ajoute aucun nouvel ID. Elle précise uniquement l'ownership architecture des tâches déjà présentes dans ce backlog.

### Sources de vérité techniques
- Entrypoint API principal: `copilot-app/backend/src/api/main.py`
- Routes modulaires: `copilot-app/backend/src/api/routes/*.py`
- Frontend runtime: `copilot-app/frontend/app/app.js` + `index.html`
- Données simulées frontend: `copilot-app/frontend/app/mockData.js`
- Gates de livraison: `scripts/run_delivery_gate.sh` + artefacts `finance-app/openclaw-gates/`

### Règles globales anti-chevauchement
- Un endpoint fonctionnel = un owner de tâche à la fois.
- Une tâche peut lire hors scope, mais ne modifie que son périmètre explicitement listé.
- Si une modification traverse 2 périmètres, elle doit être split selon les `Dependencies` existantes (pas de fusion opportuniste).
- Toute exception cross-scope doit être signalée dans `EVIDENCE` et validée par `qa` avant merge batch.

### Mode co-édition multi-agents (fichiers modifiés en parallèle)
- `docs/planning/tasks.md` est le board commun unique pour les tâches (pas de définition de tâches dans les autres docs).
- Avant édition:
  - claimer la tâche via le workboard (`scripts/parallel_workstream.py claim --role <role>`),
  - relire la section ciblée juste avant patch (`sed -n`/`rg`) pour éviter d'éditer une version périmée.
- Pendant édition:
  - patch minimal, limité à la section de la tâche claimée,
  - interdiction de refactor transverse si non requis par la tâche.
- Après édition:
  - relire le diff local (`git diff -- docs/planning/tasks.md`) et vérifier qu'aucune section d'une autre tâche n'a été modifiée,
  - si collision détectée sur la même section, ne pas écraser: merger explicitement les deux deltas et noter la résolution dans `EVIDENCE`.
- Règle de synchronisation:
  - docs Scrum (`sprint-next.md`, `product-backlog.md`) = vues de référence uniquement,
  - toute nouvelle granularité de tâche/ordre d'exécution doit d'abord être écrite dans `docs/planning/tasks.md`, puis seulement référencée ailleurs.

### Ownership architecture (tâches T-A / T-B / T-C existantes)
- `T-A1.1`
  - Owned: contrat `/api/health` uniquement.
  - Not owned: cache/freshness SLA, logique signal, UI.
- `T-A2.1` et `T-A2.2`
  - Owned: contrat `/api/stocks/prices` (mono puis multi + tests).
  - Not owned: scoring signal, widgets frontend.
- `T-A3.1` et `T-A3.2`
  - Owned: contrat `/api/news/feed` + tests dédiés.
  - Not owned: ranking avancé, orchestration UI.
- `T-A4.1`
  - Owned: unicité du chemin `/api/forecasts` (routing et contrat).
  - Not owned: moteur forecast/scoring.
- `T-A5.1`
  - Owned: robustesse `/api/copilot/ask` (fallback/erreurs).
  - Not owned: persistance historique (`/api/copilot/history`).
- `T-B1.1`, `T-B1.2`, `T-B2.1`
  - Owned: consommation frontend des endpoints MVP + transparence fallback.
  - Not owned: changement de contrat backend.
- `T-C1.1` et `T-C1.2`
  - Owned: scripts gate/runbook/orchestration.
  - Not owned: features endpoint/UI.

### Ownership architecture (Sprint W10 - tâches TV* existantes)
- `TV1-FRESH-01`
  - Owned: champs de fraîcheur (`updated_at`, `age_seconds`, `freshness_status`) sur `/api/stocks/prices`, `/api/news/feed`, `/api/forecasts`.
  - Not owned: TTL/cache policy détaillée, SLA scripts.
- `TV1-FRESH-02`
  - Owned: TTL/cache guardrails + `freshness_status=stale`.
  - Not owned: contrat signal, parcours UI.
- `TV1-FRESH-03`
  - Owned: mesure SLA et verdict script/gate.
  - Not owned: refactor endpoint métier.
- `TV2-SIGNAL-01`
  - Owned: schéma signal (`direction/confidence/action/horizon/why/risk_flag/updated_at`).
  - Not owned: extension univers complet, badges UI.
- `TV2-SIGNAL-02`
  - Owned: coverage signaux noyau (`SPY,QQQ,GLD,SLV,NVDA,TSLA`).
  - Not owned: schéma signal v1.
- `TV2-SIGNAL-03`
  - Owned: extension univers MVP + métrique couverture.
  - Not owned: adaptation UX/clickflow.
- `TV4-UI-01`
  - Owned: adapter API frontend unique pour cartes décision.
  - Not owned: logique backend signal/freshness.
- `TV4-UI-02`
  - Owned: flux 2-3 clics (navigation/assemblage UI).
  - Not owned: ajout de nouveaux contrats API.
- `TV4-UI-03`
  - Owned: badges freshness/degraded.
  - Not owned: mécanique backend SLA.
- `TV-QA-01`
  - Owned: gate E2E sprint et verdict final.
  - Not owned: développement fonctionnel endpoint/UI.

### Ownership architecture (Advance Pack - tâches TV-ADV* existantes)
- `TV-ADV-01`
  - Owned: suppression du chemin runtime mock-driven, bridge API frontend.
  - Not owned: widget Judge détaillé (TV-ADV-02), refresh orchestration (TV-ADV-03).
- `TV-ADV-02`
  - Owned: wiring widget Judge (`/api/llm/judge/run`, `/api/llm/providers/working`).
  - Not owned: refresh global UI.
- `TV-ADV-03`
  - Owned: `refreshData()` réel + synchro timestamps/states UI.
  - Not owned: calcul backend `/api/freshness`.
- `TV-ADV-04`
  - Owned: calcul réel `/api/freshness`.
  - Not owned: gate UI/clickflow.
- `TV-ADV-05`
  - Owned: persistance `/api/copilot/history` (fin mock `mock_conv_*`).
  - Not owned: endpoint agrégateur décision.
- `TV-ADV-06`
  - Owned: consolidation unique `/api/dashboard/kpis` (suppression divergence `main.py` vs `routes/dashboard.py`).
  - Not owned: autres routes dashboard non KPI.
- `TV-ADV-07`
  - Owned: endpoint agrégateur décision (`/api/decision/brief` ou équivalent validé).
  - Not owned: implémentation widget frontend complète.
- `TV-ADV-08`
  - Owned: extension couverture tests API décision.
  - Not owned: refactor métier endpoints.
- `TV-ADV-09`
  - Owned: dette de dépréciation (`@app.on_event`, `datetime.utcnow`, Pydantic v1).
  - Not owned: nouvelles features produit.
- `TV-ADV-10`
  - Owned: durcissement gate livraison (freshness/coverage/2-3 clics obligatoires).
  - Not owned: changements de contenu métier endpoints.

### Verrous de zones sensibles (pour éviter recouvrement)
- `/api/freshness` est réservé à `TV-ADV-04` (consommation seulement pour les autres).
- `/api/dashboard/kpis` est réservé à `TV-ADV-06` pendant consolidation.
- `/api/copilot/history` est réservé à `TV-ADV-05` pendant sortie du mode mock.
- `refreshData()` dans `app.js` est réservé à `TV-ADV-03`.
- `scripts/run_delivery_gate.sh` est réservé à `TV-QA-01` puis `TV-ADV-10`.

### Handoffs obligatoires entre tâches existantes
- `TV1-FRESH-01` -> `TV1-FRESH-02` -> `TV1-FRESH-03`
- `TV2-SIGNAL-01` -> `TV2-SIGNAL-02` -> `TV2-SIGNAL-03`
- `TV4-UI-01` -> `TV4-UI-02` -> `TV4-UI-03`
- `TV-ADV-01` -> `TV-ADV-02` et `TV-ADV-03`
- `TV-ADV-04`, `TV-ADV-05`, `TV-ADV-06`, `TV-ADV-07` -> `TV-ADV-08` -> `TV-ADV-10`

## Modèle de référence: Judge API (à réutiliser pour les autres endpoints)
- **Implémentation canonique**: `copilot-app/backend/src/api/routes/judge.py` (GET `/api/judge`).
- **Pourquoi c'est le modèle**: l'endpoint montre le pattern complet "production-ready" (normalisation input, cache TTL, debug bypass, validation Pydantic, parsing JSON strict, multi-provider fallback, contrat typé pour le frontend).
- **Dépendances à réutiliser (backend)**:
  - Response envelope: `copilot-app/backend/src/core/response.py` (`ok/err`) ou enveloppe `{"ok":true,"data":...}` équivalente.
  - Normalisation tickers: `copilot-app/backend/src/core/ticker_normalization.py` (`normalize_ticker`, `normalize_tickers`).
  - Pipeline/validation: `copilot-app/backend/src/services/judge_pipeline.py` (`build_payload`, `parse_llm_answer`, `validate_llm_response`).
  - Canonicalisation typée: `copilot-app/backend/src/services/judge_builder.py` + `copilot-app/backend/src/schemas/judge.py`.
  - Clients LLM fallback: `copilot-app/backend/src/services/g4f_client.py`, `copilot-app/backend/src/services/codestral_client.py`, `copilot-app/backend/src/services/groq_client.py`.
  - Working models list (g4f): `copilot-app/backend/src/agents/g4f_model_watcher.py` + endpoint debug `GET /api/llm/providers/working` (déjà présent dans `main.py`).
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS** (checklist copy-paste par endpoint):
  - Avant de créer du code, **chercher** un helper existant (normalisation tickers, cache TTL, downsample, storage loader) et le réutiliser.
  - Garder un contrat stable: `ok/data` + champs standard `generated_at`, `freshness|timestamp`, `source[]`, `filters_applied`, `stats`, `warnings` (même si vide).
  - Ajouter un flag `debug=true` (query) qui:
    - **désactive le cache**, et
    - expose uniquement en debug: `debug_pipeline` (traces), `debug_payload`, `debug_llm_res` (jamais en nominal).
  - Cache TTL: utiliser le pattern Judge (key dérivée des params + TTL + prune). Si vous devez partager un cache, préférer `copilot-app/backend/src/core/cache.py` (`TTLCache`) ou les helpers `_response_cache_*` existants dans `copilot-app/backend/src/api/main.py` (éviter d'introduire un nouveau cache ad-hoc).
  - LLM: forcer un format **JSON strict sur une seule ligne**, valider avant/après via Pydantic, et implémenter une chaîne de fallback (OpenRouter->g4f->Codestral->Groq) sans casser le contrat "never-empty".

---

## T-A1.1 — Verrouiller contrat `/api/health`
- **Objectif**: réponse health stable et rétro-compatible.
- **Scope IN**: normalisation shape + tests.
- **Scope OUT**: ajout observabilité avancée.
- **Prérequis**: backend bootable.
- **Fichiers cibles**: `copilot-app/backend/src/api/main.py`, `copilot-app/backend/tests/test_health.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser le pattern Judge: enveloppe `ok/data` + `generated_at` + `source[]` (même si `/api/health` est simple).
  - Aligner les clés storage sur le reste du backend: préférer `storage.io.load_json("forecasts")`, `load_json("news_feed")`, `load_json("brief_weekly")`, `load_json("backtests")` (éviter les variantes `"*.json"` si pas nécessaires).
  - Ne pas renommer des clés existantes: ajouter des alias (ex: `timestamp`/`generated_at`) pour préserver compat client/tests.
- **Plan implémentation**:
  1. Définir schéma attendu (top-level + data).
  2. Harmoniser champs `status`.
  3. Ajuster/ajouter tests.
- **Critères d’acceptation testables**:
  - Endpoint renvoie 200 + `ok=true`.
  - `data.timestamp` présent.
- **Commandes de test**:
  - `curl -sS http://localhost:8050/api/health | jq`
  - `cd copilot-app/backend && ([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && .venv/bin/pytest -q tests/test_health.py`
- **Evidences attendues**: payload health + pytest vert.
- **Risques**: clients dépendants anciens champs.
- **Dépendances**: aucune.

## T-A2.1 — Unifier réponse mono ticker `/api/stocks/prices`
- **Objectif**: contrat UI-friendly pour 1 ticker.
- **Scope IN**: champs `ticker, points, count, timestamp`.
- **Scope OUT**: provider data externe.
- **Prérequis**: snapshot `stocks/prices` ou fallback actif.
- **Fichiers cibles**: `copilot-app/backend/src/api/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser la normalisation existante: `core/ticker_normalization.py` (pas de parsing custom des tickers).
  - Réutiliser le cache TTL déjà en place (`_response_cache_key/_get/_set` + `STOCKS_PRICES_CACHE_TTL_SECONDS`) au lieu d'introduire un nouveau cache.
  - Réutiliser le downsampling existant (`_downsample_points` / `core.downsample.lttb`) pour garder un payload UI léger.
  - Garder le contrat mono-ticker comme "subset" du multi-ticker (mêmes champs standard: `generated_at`, `freshness|timestamp`, `source[]`, `filters_applied`, `stats`, `warnings`).
- **Plan implémentation**:
  1. Vérifier mapping mono ticker.
  2. Garantir présence clés même si vide.
- **Critères d’acceptation testables**:
  - Requête `ticker=SPY` renvoie schéma conforme.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq`
- **Evidences attendues**: JSON de référence stocké dans artefact.
- **Risques**: data manquante selon environnement.
- **Dépendances**: T-A1.1.

## T-A2.2 — Tester multi ticker `/api/stocks/prices`
- **Objectif**: valider payload map multi-tickers.
- **Scope IN**: tests de contrat + cas erreur input.
- **Scope OUT**: optimisation perfs.
- **Prérequis**: T-A2.1.
- **Fichiers cibles**: `copilot-app/backend/tests/test_stocks_prices_contract.py` (nouveau)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser les mêmes invariants que Judge: "never-empty" (pas de 500), `ok/data`, et clés stables (`count`, `timestamp|freshness`, `source[]`, `filters_applied`, `stats`, `warnings`).
  - Éviter les appels réseau dans les tests (pas de dépendance FRED/YFinance): baser le test sur la shape + fallback contract (payload vide acceptable, mais structure obligatoire).
- **Plan implémentation**:
  1. Ajouter tests `tickers=SPY,QQQ`.
  2. Ajouter test paramètre manquant.
- **Critères d’acceptation testables**:
  - Tests passent.
  - Aucun 500 en cas input incomplet.
- **Commandes de test**:
  - `cd copilot-app/backend && ([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && .venv/bin/pytest -q tests/test_stocks_prices_contract.py`
- **Evidences attendues**: rapport pytest.
- **Risques**: divergence selon fixtures data.
- **Dépendances**: T-A2.1.

## T-A3.1 — Normaliser `news_feed` items
- **Objectif**: items news exploitables et homogènes.
- **Scope IN**: mapping title/url/source/date/tickers/score.
- **Scope OUT**: scoring algorithmique news.
- **Prérequis**: endpoint existant.
- **Fichiers cibles**: `copilot-app/backend/src/api/main.py`, `copilot-app/backend/src/api/services/news_service.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser les helpers existants de normalisation (timestamps, `source[]`, filtrage fenêtre) au lieu de recoder un mapping.
  - Réutiliser `core/ticker_normalization.py` via la résolution tickers déjà utilisée côté `/api/news/feed` (éviter les filtres tickers fragiles).
  - Conserver l'alias compat `articles` (en plus de `items`) tant que le frontend n'est pas migré.
  - Garder les champs standard Judge: `generated_at`, `freshness|last_update`, `source[]`, `filters_applied`, `stats`, `warnings`.
- **Plan implémentation**:
  1. Unifier format `items`.
  2. Garder alias `articles` pour compat.
- **Critères d’acceptation testables**:
  - `items` non nul, `count` cohérent.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq`
- **Evidences attendues**: 1 payload exemple normalisé.
- **Risques**: variabilité schema source raw news.
- **Dépendances**: T-A1.1.

## T-A3.2 — Tests contrat `news_feed`
- **Objectif**: figer le contrat minimal dans des tests.
- **Scope IN**: tests items/limit/filter tickers.
- **Scope OUT**: perf tests.
- **Prérequis**: T-A3.1.
- **Fichiers cibles**: `copilot-app/backend/tests/test_news_feed_contract.py` (nouveau)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Tester le contrat (shape) avant le contenu: `ok`, `data.items`, `data.count`, `data.generated_at`, `data.source[]`.
  - Ajouter un test `tickers=SPY,QQQ` qui accepte le fallback "filter relaxed" (warning) mais refuse un 500.
- **Plan implémentation**:
  1. Ecrire tests nominal + edge cases.
  2. Valider non-régression.
- **Critères d’acceptation testables**:
  - pytest vert.
- **Commandes de test**:
  - `cd copilot-app/backend && ([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && .venv/bin/pytest -q tests/test_news_feed_contract.py`
- **Evidences attendues**: rapport pytest.
- **Risques**: dépendance aux fixtures runtime.
- **Dépendances**: T-A3.1.

## T-A4.1 — Confirmer route unique `/api/forecasts`
- **Objectif**: éviter ambiguïtés d’implémentation forecasts.
- **Scope IN**: route active unique via router.
- **Scope OUT**: calcul des scores forecast.
- **Prérequis**: boot backend OK.
- **Fichiers cibles**: `copilot-app/backend/src/api/main.py`, `copilot-app/backend/src/api/routes/forecasts.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Prendre `/api/judge` comme modèle: un seul chemin "source of truth" + cache TTL + `debug=true` pour bypass cache et traces.
  - Réutiliser `src/core/response.ok/err` (routes modulaires) et harmoniser l'enveloppe (`ok/data`) avec `main.py` si nécessaire, au lieu de créer une 3e variante.
  - S'assurer que `/api/forecasts` lit les mêmes sources que Judge (`storage.io.load_json("forecasts")`) pour éviter des divergences "forecasts.json" vs "forecasts".
- **Plan implémentation**:
  1. Vérifier include_router.
  2. Supprimer incohérences commentaire/code.
- **Critères d’acceptation testables**:
  - `GET /api/forecasts` stable (10 appels sans 500).
- **Commandes de test**:
  - `for i in {1..10}; do curl -sS http://localhost:8050/api/forecasts >/dev/null; done; echo OK`
- **Evidences attendues**: log boucle OK + payload exemple.
- **Risques**: dépendance data forecasts périmée.
- **Dépendances**: T-A1.1.

## T-A5.1 — Hardening `/api/copilot/ask`
- **Objectif**: robustesse cas sans source/LLM indisponible.
- **Scope IN**: erreurs contrôlées, champs qualité.
- **Scope OUT**: amélioration modèle LLM.
- **Prérequis**: modules research importables.
- **Fichiers cibles**: `copilot-app/backend/src/api/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser le client existant `copilot-app/backend/src/research/llm_client.py` (`ask_llm`) et aligner son fallback sur le pattern Judge (toujours `answer` non vide + `sources[]` + `generated_at` + `source[]`).
  - Si un fallback g4f est requis, préférer `services/g4f_client.call_g4f` (sélection modèle/provider + retour normalisé) plutôt que des appels g4f inline.
  - Ajouter un mode `debug` (query/body) qui expose `model/provider` + `citations` et garde le nominal compact.
- **Plan implémentation**:
  1. Encadrer try/except avec messages déterministes.
  2. Garantir shape de fallback.
- **Critères d’acceptation testables**:
  - Réponse toujours avec `answer` + `sources`.
- **Commandes de test**:
  - `curl -sS -X POST "http://localhost:8050/api/copilot/ask" -H 'Content-Type: application/json' -d '{"question":"Etat marché"}' | jq`
- **Evidences attendues**: payload nominal/fallback.
- **Risques**: latence ou indisponibilité provider LLM.
- **Dépendances**: T-A1.1.

## T-B1.1 — Créer couche API frontend minimale
- **Objectif**: centraliser fetch MVP.
- **Scope IN**: helper fetch + timeout + gestion erreurs.
- **Scope OUT**: migration framework frontend.
- **Prérequis**: contrats API A stabilisés.
- **Fichiers cibles**: `copilot-app/frontend/app/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser le pattern backend Judge: toutes les réponses sont `ok/data` (et potentiellement `source[]`, `freshness`). Le wrapper `fetchJson` doit normaliser ces champs sans "adapter" au cas par cas.
  - Réutiliser les IDs DOM + fonctions existantes dans `app.js` (pas de rewrite UI). Objectif: brancher, pas redesign.
- **Plan implémentation**:
  1. Ajouter wrapper `fetchJson`.
  2. Mapper endpoints MVP.
- **Critères d’acceptation testables**:
  - Les appels MVP passent via wrapper unique.
- **Commandes de test**:
  - Test manuel navigateur + Network tab.
- **Evidences attendues**: extrait code + capture réseau.
- **Risques**: side-effects sur fonctions legacy.
- **Dépendances**: T-A2.1, T-A3.1, T-A4.1, T-A5.1.

## T-B1.2 — Brancher widgets MVP aux données API
- **Objectif**: afficher health/news/forecasts/stocks réels.
- **Scope IN**: mapping payload -> render.
- **Scope OUT**: redesign complet UI.
- **Prérequis**: T-B1.1.
- **Fichiers cibles**: `copilot-app/frontend/app/app.js`, `copilot-app/frontend/app/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser les widgets existants (ne pas en recréer):
    - `copilot-app/frontend/app/components/widgets/kpi-cards-pro.html`
    - `copilot-app/frontend/app/components/widgets/forecast-scenarios.html`
    - `copilot-app/frontend/app/components/widgets/news-feed.html`
    - `copilot-app/frontend/app/components/widgets/llm-judge.html`
  - Réutiliser le loader `copilot-app/frontend/app/js/utils/componentLoader.js` et garder le mapping `{path,target}` comme source de vérité de chargement.
  - Toujours rendre visible le `source`/`freshness` si fourni par l'API (sinon marquer fallback).
- **Plan implémentation**:
  1. Identifier widgets MVP.
  2. Injecter data API et loading states.
- **Critères d’acceptation testables**:
  - Widgets affichent data API lorsque backend up.
- **Commandes de test**:
  - Ouvrir `http://localhost:5173` + refresh hard.
- **Evidences attendues**: screenshots widgets remplis.
- **Risques**: couplage DOM fragile.
- **Dépendances**: T-B1.1.

## T-B2.1 — Badge « Données simulées »
- **Objectif**: transparence utilisateur fallback.
- **Scope IN**: badge visible par composant fallback.
- **Scope OUT**: système de feature flags global.
- **Prérequis**: B1 en place.
- **Fichiers cibles**: `copilot-app/frontend/app/app.js`, `copilot-app/frontend/app/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Utiliser les champs backend standard (`source[]`, `warnings[]`, `freshness`) pour décider du badge au lieu d'heuristiques fragiles.
  - Le badge doit être par-widget (pas un global) pour refléter les dégradations partielles (pattern Judge: contract never-empty + warnings).
- **Plan implémentation**:
  1. Ajouter booléen `isMockSource` par bloc.
  2. Rendre badge conditionnel.
- **Critères d’acceptation testables**:
  - Badge visible quand backend down ou data absente.
- **Commandes de test**:
  - Stop backend puis reload UI.
- **Evidences attendues**: captures backend up/down.
- **Risques**: faux positifs de fallback.
- **Dépendances**: T-B1.2.

## T-C1.1 — Script gate MVP PASS/BLOCKED
- **Objectif**: une commande de gate unique.
- **Scope IN**: health + 4 endpoints + copilot ask + smoke.
- **Scope OUT**: tests perfs.
- **Prérequis**: tâches A/B principales.
- **Fichiers cibles**: `skills/finance-regression-gate/` ou `scripts/` + `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser les gates existants (`scripts/backend_regression_gate.sh`, `scripts/run_delivery_gate.sh`) et compléter plutôt que créer un nouveau framework.
  - Les checks doivent consommer les endpoints via le contrat `ok/data` et remonter les `source[]/warnings[]` (pattern Judge) dans l'artefact final.
- **Plan implémentation**:
  1. Écrire script gate idempotent.
  2. Générer rapport markdown/json horodaté.
- **Critères d’acceptation testables**:
  - Sortie claire PASS/BLOCKED.
  - Rapport créé sous `finance-app/openclaw-gates/`.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - `bash <script_gate>.sh`
- **Evidences attendues**: rapport gate + code retour shell.
- **Risques**: dépendances externes ponctuellement indisponibles.
- **Dépendances**: A1..A2 (gate initial), puis A3..A5 et B1..B2 pour le gate final.

## T-C1.2 — Runbook orchestration MVP (codex/OpenClaw)
- **Objectif**: standardiser dispatch/monitoring des tâches.
- **Scope IN**: prompts par rôle, cadence check, format preuves.
- **Scope OUT**: auto-remédiation complète.
- **Prérequis**: OpenClaw opérationnel (cron + runner tmux).
- **Fichiers cibles**:
  - `docs/planning/mvp-plan.md`
  - `docs/planning/tasks.md`
  - `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
  - `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`
  - `scripts/preflight_dispatch.sh`
  - `scripts/validate_roles_sequential.sh`
  - `scripts/run_delivery_gate.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Référencer explicitement le modèle Judge (section "Modèle de référence: Judge API") pour les conventions de contrat/caching/debug sur tous les endpoints du runbook.
  - Standardiser la collecte d'évidences: pour chaque endpoint, capturer un payload JSON + mentionner `source[]` et `freshness` dans l'artefact.
- **Plan implémentation**:
  1. Préflight (états + santé soft).
  2. Exécution séquentielle stricte par batch (planner->dev->tester->qa).
  3. Publication artefact de preuve + `run_delivery_gate`.
- **Critères d’acceptation testables**:
  - Un batch produit: contrats (8 clés) + un artefact `openclaw-gates/` gateable.
- **Commandes de test**:
  - `bash scripts/preflight_dispatch.sh`
  - `SEQUENTIAL_VALIDATE_TIMEOUT_SECONDS=480000 bash scripts/validate_roles_sequential.sh --roles planner,dev,tester,qa --strict-ready-chain --chain-target BATCH-XX`
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/batch-XX-<timestamp>.md`
- **Evidences attendues**:
  - `finance-app/openclaw-gates/batch-XX-<timestamp>.md`
  - `logs-codex-runs/role-runner/sequential-validate-*.jsonl`
- **Risques**: saturation context/token selon prompts.
- **Dépendances**: T-C1.1.

---

## Pack de dispatch (delta incrémental)

### Batch-01
- **Tâches**: `T-A1.1`, `T-A2.1`
- **Instruction commune agents**:
  - livrer strictement le scope IN
  - joindre commandes exactes exécutées
  - joindre preuves minimales (payload JSON + sortie tests)
  - terminer avec contrat complet (8 clés) et verdict `PASS|BLOCKED` motivé
- **Blocage immédiat si**:
  - absence de section EVIDENCE
  - test non exécuté
  - contrat API modifié sans test mis à jour
- **Chemin artefact obligatoire**:
  - `finance-app/openclaw-gates/batch-01-<timestamp>.md`
  - contenu minimal: `DELTA`, `EVIDENCE`, `RISKS`, `NEXT`, `VERDICT`, `BLOCKER_ID`, `NEXT_ACTION_UNIQUE`

### Handoff checklist QA (delta 20:05)
- [ ] Scope IN respecté pour chaque tâche du batch
- [ ] Au moins 1 commande de test exécutée par tâche
- [ ] Évidence textuelle copiée dans artefact gate
- [ ] Verdict explicite `PASS` ou `BLOCKED`
- [ ] Prochaine action unique définie

## Ordonnancement recommandé
1. T-A1.1
2. T-A2.1 → T-A2.2
3. T-A3.1 → T-A3.2
4. T-A4.1
5. T-A5.1
6. T-B1.1 → T-B1.2
7. T-B2.1
8. T-C1.1 → T-C1.2

## Delta tâches (cycle 20:20)

### Delta 20:20 — commandes renforcées pour `T-A1.1`
- Ajouter boucle stabilité:
  - `for i in {1..3}; do curl -sS http://localhost:8050/api/health | jq -c '{ok,status,ts:.data.timestamp}'; done`
- Critère additionnel: 3/3 réponses exploitables, sans clé absente.

### Delta 20:20 — commandes renforcées pour `T-A2.1`
- Ajouter vérification robuste des clés:
  - `for i in {1..5}; do curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq -c '{ok,ticker,count,has_points:(.data.points!=null),has_ts:(.data.timestamp!=null)}'; done`
- Critère additionnel: 5/5 réponses sans erreur serveur.

### Template d’évidence obligatoire (toutes tâches Batch-01)
```text
STATUS:
DELTA:
EVIDENCE: task_update=...;lock_check=ok;stream_id=<BATCH-ID>;task_id=<...>;cmd=...;tests_run=...
RISKS:
NEXT:
VERDICT: PASS|BLOCKED
BLOCKER_ID: NONE|...
NEXT_ACTION_UNIQUE:
```

## Delta runbook tâches (cycle 20:35)

### Lot prêt à exécution immédiate (Batch-01)
1. **T-A1.1**
   - Owner: `dev`
   - QA gate: `tester` valide commandes, `qa` signe verdict
2. **T-A2.1**
   - Owner: `dev`
   - QA gate: stabilité 5x obligatoire avant verdict

### Lot conditionnel suivant (Batch-02)
1. **T-A2.2** (tests multi-ticker)
2. **T-A3.1** (normalisation news)

**Règle d’activation Batch-02**: présence de `VERDICT: PASS` dans `finance-app/openclaw-gates/batch-01-<timestamp>.md`.

### Template d’assignation agent (copier-coller)
```text
[TASK_ID] <id>
OBJECTIF: <objectif court>
SCOPE_IN: <liste>
SCOPE_OUT: <liste>
PREREQUIS: <liste>
FICHIERS_CIBLES: <liste>
PLAN_IMPLEMENTATION: <3-5 étapes>
ACCEPTANCE_TESTABLE: <points vérifiables>
COMMANDES_TEST: <commandes exactes>
EVIDENCES_ATTENDUES: <artefacts + extraits>
RISQUES: <liste>
DEPENDANCES: <liste>
VERDICT_ATTENDU: PASS|BLOCKED
```

## Delta dispatch tâches (cycle 20:50)

### Pack Batch-02 (préparé, verrouillé)

#### Carte d’assignation prête pour `T-A2.2`
```text
[TASK_ID] T-A2.2
OBJECTIF: valider contrat multi-ticker /api/stocks/prices
SCOPE_IN: tests tickers=SPY,QQQ; test input incomplet; absence de 500
SCOPE_OUT: optimisation perf; refactor endpoint
PREREQUIS: VERDICT PASS Batch-01
FICHIERS_CIBLES: copilot-app/backend/tests/test_stocks_prices_contract.py
PLAN_IMPLEMENTATION: écrire tests -> exécuter -> corriger si rouge -> re-run vert
ACCEPTANCE_TESTABLE: pytest vert; map multi-ticker stable; cas incomplet non bloquant
COMMANDES_TEST: cd copilot-app/backend && ([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && .venv/bin/pytest -q tests/test_stocks_prices_contract.py
EVIDENCES_ATTENDUES: sortie pytest + payload multi-ticker de référence
RISQUES: fixtures data divergentes
DEPENDANCES: T-A2.1
VERDICT_ATTENDU: PASS|BLOCKED
```

#### Carte d’assignation prête pour `T-A3.1`
```text
[TASK_ID] T-A3.1
OBJECTIF: normaliser le contrat /api/news/feed
SCOPE_IN: items/count + alias articles + fallback contrôlé
SCOPE_OUT: ranking news avancé
PREREQUIS: VERDICT PASS Batch-01
FICHIERS_CIBLES: copilot-app/backend/src/api/main.py; copilot-app/backend/src/api/services/news_service.py
PLAN_IMPLEMENTATION: normaliser mapping -> garder compat alias -> valider payload
ACCEPTANCE_TESTABLE: items non nul; count cohérent; aucune 500 en nominal
COMMANDES_TEST: curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq
EVIDENCES_ATTENDUES: payload normalisé + verdict QA
RISQUES: qualité variable des entrées news
DEPENDANCES: T-A1.1
VERDICT_ATTENDU: PASS|BLOCKED
```

### Règle de lot
- Batch-02 est exécuté en séquence stricte `T-A2.2` puis `T-A3.1`.
- Si `T-A2.2` est BLOCKED, ne pas lancer `T-A3.1`.

## Delta tâches (cycle 21:05)

### Contrôle qualité lot (ajout)
- **Nouvelle exigence commune Batch-01/Batch-02**:
  - inclure `VERDICT: PASS|BLOCKED`
  - inclure `BLOCKER_ID` (ou `NONE`)
  - inclure `NEXT_ACTION_UNIQUE`

### Patch minimal policy (ajout)
- En cas `BLOCKED`, l’agent `dev` doit proposer un patch minimal ciblé sur le fichier fautif listé dans `BLOCKER_ID`.
- Interdiction d’ouvrir des fichiers hors scope de la tâche sans justification QA.

### Evidence quality gate (ajout)
- Toute commande de test listée dans la tâche doit avoir soit:
  1) sortie utile incluse dans l’artefact, soit
  2) motif documenté de non-exécution.

## Changelog
- 2026-02-24 19:50 America/New_York — Ajout du pack de dispatch Batch-01 avec règles de preuve et conditions de blocage immédiat.
- 2026-02-24 20:05 America/New_York — Ajout du chemin d’artefact obligatoire pour Batch-01 et d’une checklist QA de handoff pour fiabiliser le verdict.
- 2026-02-24 20:20 America/New_York — Renforcement incrémental des tâches Batch-01 (boucles de stabilité health/stocks) + template d’évidence unifié PASS/BLOCKED.
- 2026-02-24 20:35 America/New_York — Ajout d’un runbook de lot (Batch-01 immédiat, Batch-02 conditionnel), règle d’activation explicite via artefact gate, et template d’assignation standardisé.
- 2026-02-24 20:50 America/New_York — Préparation du pack Batch-02 avec cartes d’assignation complètes pour T-A2.2/T-A3.1 et règle de séquencement bloquant.
- 2026-02-24 21:05 America/New_York — Ajout d’exigences communes d’artefacts (VERDICT/BLOCKER_ID/NEXT_ACTION_UNIQUE), politique de patch minimal en cas BLOCKED, et gate qualité des preuves pour toutes commandes de test listées.
- 2026-02-24 22:05 America/New_York — Alignement tâches sur environnement VM: commandes pytest auto-bootstrap + dépendances C1 réalignées pour éviter cycle avec lot A.
- 2026-02-26 14:10 America/New_York — Alignement complet sur orchestration codex-only/OpenClaw: suppression des mentions legacy et adoption du runbook `preflight_dispatch` + `validate_roles_sequential` + `run_delivery_gate`.
- 2026-02-26 America/New_York — Intégration d’un cadrage architecture anti-chevauchement sur les tâches existantes (ownership par task ID, verrous de zones sensibles, handoffs obligatoires), sans création de nouveaux IDs.
- 2026-02-26 America/New_York — Ajout du mode co-édition multi-agents: protocole claim/edit/merge, synchronisation stricte vers board commun `docs/planning/tasks.md`.

## Vision Task Pack - Sprint W10 (P0-first)

Source:
- `docs/planning/PRODUCT_VISION.md`
- `docs/scrum/sprint-next.md`

Execution rule:
- Keep tasks 2-4h each.
- Close only with contract output + test evidence.
- Prioritize user-visible decision flow over refactor work.

### TV1-FRESH-01 - Freshness metadata contract (P0)
- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: rendre la fraicheur visible et cohérente sur les endpoints core.
- **Scope IN**:
  - standardiser `updated_at`, `age_seconds`, `freshness_status` sur:
    - `/api/stocks/prices`
    - `/api/news/feed`
    - `/api/forecasts`
- **Scope OUT**: optimisation perf profonde des providers.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/routes/forecasts.py`
- **Acceptation testable**:
  - les 3 endpoints exposent les 3 champs de fraicheur.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq`
  - `curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq`
  - `curl -sS "http://localhost:8050/api/forecasts" | jq`
- **Dependencies**: none

### TV1-FRESH-02 - Cache TTL and stale guardrails (P0)
- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: garantir la cible <=10 minutes sur surfaces critiques.
- **Scope IN**:
  - TTL cache configurable pour prices/news/forecasts
  - fallback explicite si data stale (`freshness_status=stale`)
- **Scope OUT**: stockage distribue/cache externe.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/services/news_service.py`
- **Acceptation testable**:
  - aucun fallback silencieux; stale signalé explicitement.
- **Commandes de test**:
  - `cd copilot-app/backend && .venv/bin/pytest -q tests/test_endpoint_cache_contracts.py`
- **Dependencies**: TV1-FRESH-01

### TV1-FRESH-03 - Freshness SLA checker (P0)
- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: mesurer et prouver le SLA de fraicheur.
- **Scope IN**:
  - script de contrôle SLA (>=90% cycles <=10m)
  - sortie PASS/BLOCKED + métriques
- **Scope OUT**: monitoring cloud externe.
- **Fichiers cibles**:
  - `scripts/`
  - `finance-app/openclaw-gates/`
- **Acceptation testable**:
  - un run produit un verdict SLA auditable.
- **Commandes de test**:
  - `bash scripts/preflight_dispatch.sh`
  - `bash <freshness_sla_script>.sh`
- **Dependencies**: TV1-FRESH-02

### TV2-SIGNAL-01 - Decision signal schema v1 (P0)
- **Epic**: Epic 2 - Forecast Engine
- **Objectif**: figer le contrat de signal utilisé par backend+frontend.
- **Scope IN**:
  - contrat par actif/secteur:
    - `direction`, `confidence`, `action`, `horizon`, `why`, `risk_flag`, `updated_at`
  - mapping backend vers payload frontend.
- **Scope OUT**: algorithme avancé de scoring.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/schemas.py`
- **Acceptation testable**:
  - contrat stable et sans champ manquant.
- **Commandes de test**:
  - `cd copilot-app/backend && .venv/bin/pytest -q`
- **Dependencies**: TV1-FRESH-01

### TV2-SIGNAL-02 - Core asset signals (P0)
- **Epic**: Epic 2 - Forecast Engine
- **Objectif**: livrer un signal exploitable sur noyau d’actifs prioritaire.
- **Scope IN**:
  - actifs: `SPY, QQQ, GLD, SLV, NVDA, TSLA`
  - horizons: `1-3d` et `1-2w`
- **Scope OUT**: univers complet MVP.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/core/`
- **Acceptation testable**:
  - chaque actif retourne direction+confidence+action+updated_at.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/stocks/prices?tickers=SPY,QQQ,GLD,SLV,NVDA,TSLA" | jq`
- **Dependencies**: TV2-SIGNAL-01

### TV2-SIGNAL-03 - Full MVP universe coverage (P0)
- **Epic**: Epic 2 - Forecast Engine
- **Objectif**: étendre la couverture au périmètre vision MVP.
- **Scope IN**:
  - indices: `SPY, QQQ, DIA, IWM`
  - metals: `GLD, SLV`
  - AI/mega-cap: `NVDA, MSFT, AMZN, GOOGL, META, TSLA, AAPL`
  - sectors: `XLK, XLE, XLF, XLV, XLI`
- **Scope OUT**: actifs hors univers MVP.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/data/`
- **Acceptation testable**:
  - >=90% univers avec signal complet par cycle.
- **Commandes de test**:
  - `cd copilot-app/backend && .venv/bin/pytest -q tests/test_stocks_prices_contract.py`
- **Dependencies**: TV2-SIGNAL-02

### TV4-UI-01 - Decision cards API adapter (P1 but sprint-committed)
- **Epic**: Epic 4 - Decision Cockpit Frontend
- **Objectif**: brancher frontend sur le contrat de signal backend.
- **Scope IN**:
  - adapter fetch unique pour signals/freshness
  - gestion loading/error claire
- **Scope OUT**: redesign UI complet.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
- **Acceptation testable**:
  - appels API centralisés et traçables.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - validation manuelle `http://localhost:5173`
- **Dependencies**: TV2-SIGNAL-01

### TV4-UI-02 - 2-3 click daily brief flow (P1 but sprint-committed)
- **Epic**: Epic 4 - Decision Cockpit Frontend
- **Objectif**: obtenir "quoi faire aujourd’hui" en 2-3 interactions.
- **Scope IN**:
  - vue synthèse avec action recommandée
  - navigation rapide actifs/secteurs prioritaires
- **Scope OUT**: navigation avancée multi-pages.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/index.html`
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/style.css`
- **Acceptation testable**:
  - flux complet <=3 clics vers briefing actionnable.
- **Commandes de test**:
  - test manuel + capture parcours.
- **Dependencies**: TV4-UI-01

### TV4-UI-03 - Freshness and degraded-state badges (P1 but sprint-committed)
- **Epic**: Epic 4 - Decision Cockpit Frontend
- **Objectif**: rendre explicite l’état des données.
- **Scope IN**:
  - badge `fresh/stale/degraded`
  - affichage `updated_at` sur chaque carte
- **Scope OUT**: alerting mobile/push.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/style.css`
- **Acceptation testable**:
  - aucun état caché: stale/degraded toujours visible.
- **Commandes de test**:
  - stop partiel backend/source -> vérifier rendu degradé.
- **Dependencies**: TV1-FRESH-01, TV4-UI-01

### TV-QA-01 - Sprint W10 end-to-end gate (P0 release gate)
- **Epic**: Cross-epic quality gate
- **Objectif**: valider le sprint sur workflow utilisateur final.
- **Scope IN**:
  - test e2e backend+frontend
  - mesure des métriques sprint (freshness/coverage/clicks)
  - artefact final PASS/BLOCKED
- **Scope OUT**: tests non-MVP.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
  - `docs/scrum/sprint-next.md`
- **Acceptation testable**:
  - artefact final signé QA avec verdict et blocker_id.
- **Commandes de test**:
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/sprint-w10-<timestamp>.md`
- **Dependencies**:
  - TV1-FRESH-03
  - TV2-SIGNAL-03
  - TV4-UI-03

### Ready-next queue (after W10 commit)
- TV3-JUDGE-01 - Multi-provider opinion collector (g4f-first).
  - INTEGRATION-APP-EENGINEER-RECOMMENDATIONS:
    - Réutiliser le pattern `/api/judge` (cache TTL + debug bypass + Pydantic + JSON strict) comme squelette de l'endpoint.
    - g4f: réutiliser `services/g4f_client.call_g4f` + la liste `tested_g4f_models*_*.json` (pas d'appel g4f inline).
    - Réutiliser `agents/g4f_model_watcher.py` + `GET /api/llm/providers/working` pour piloter le choix des modèles/latences.
- TV3-JUDGE-02 - Judge arbitration output (`final_action`, `confidence_delta`, `conflict_mode`).
  - INTEGRATION-APP-EENGINEER-RECOMMENDATIONS:
    - Réutiliser `services/judge_builder.py` + `schemas/judge.py` pour figer un contrat canonique (et éviter une 2e shape "judge-like").
    - Conserver `source[]/warnings[]/generated_at` et exposer explicitement `fallback_used` quand une étape LLM échoue (pattern Judge).
- TV5-ASK-01 - Ask Copilot deep analysis with grounded context.
  - INTEGRATION-APP-EENGINEER-RECOMMENDATIONS:
    - Réutiliser `research/llm_client.ask_llm` (OpenAI->g4f->fallback) et aligner la réponse sur l'enveloppe Judge (`ok/data`, `sources[]`, `generated_at`, `source[]`).
    - Éviter d'introduire une nouvelle logique de RAG: s'appuyer sur `rag_store`/chunks existants et stabiliser le contrat + tests.

## Changelog (vision tasks)
- 2026-02-26 America/New_York - Added W10 vision-aligned task pack prioritized by P0 user-value and freshness constraints.

## Code-Audit Advance Pack (pre-W11)

Source audit (2026-02-26):
- frontend still relies heavily on `mockData.js` and simulated flows in `app.js`
- `/api/freshness` in `main.py` is currently placeholder/static
- `/api/copilot/history` currently returns mock conversations
- duplicate KPI logic exists between `main.py:/api/dashboard/kpis` and `routes/dashboard.py:/kpis`
- tests currently cover mainly `health`, `stocks/prices`, `news/feed`; several decision endpoints are untested
- backend has deprecation debt (`@app.on_event`, `datetime.utcnow`, pydantic v1 validators/max_items)

### UI Fast-Lane Priority (concrete user-visible results)
1. `TV-ADV-01-D2` - Runtime wiring of priority widgets
2. `TV-ADV-02` - Judge widget real wiring
3. `TV-ADV-03` - Real refresh behavior in UI
4. `TV-ADV-07` - Single decision-brief endpoint for 2-3 click flow
5. `TV-ADV-10` - Gate upgrade tied to UI workflow proof

### TV-ADV-01 - Frontend API bridge (remove mock-driven runtime path)
- **Epic**: Epic 4 - Decision Cockpit Frontend
- **Objectif**: remplacer le chemin principal mock par des appels backend réels.
- **Scope IN**:
  - créer un client API frontend centralisé (timeout + erreur + retry léger)
  - brancher widgets décision à API réelle (kpis, forecasts, news, recommendations)
- **Scope OUT**: suppression totale de tous les composants non-MVP.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/mockData.js`
  - `copilot-app/frontend/app/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser les widgets existants (référence: `copilot-app/frontend/app/components/widgets/`) et limiter le travail à "wiring + states" (pas de nouveaux composants).
  - Réutiliser le loader `componentLoader.js` et garder `index.html` comme inventaire de widgets chargés.
  - Propager des métadonnées backend standard vers l'UI (`source[]`, `freshness`, `warnings[]`) pour rendre le dégradé visible (pattern Judge).
- **Acceptation testable**:
  - le flux principal ne dépend plus de `mockData.js` en mode nominal backend up.
- **Dependencies**: TV4-UI-01

#### Breakdown for `TV-ADV-01` (ready to launch)

##### TV-ADV-01-P - Planner scope lock and widget map
- **Owner**: planner
- **Objectif**: verrouiller le mapping API -> widgets MVP à migrer en premier.
- **Scope IN**:
  - identifier widgets décision critiques (kpi, forecasts, news, recommendations, judge trigger)
  - définir pour chaque widget: endpoint, contrat requis, fallback explicite
- **Scope OUT**: implémentation JS.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/index.html`
  - `docs/planning/tasks.md` (notes de dispatch si besoin)
- **Evidence attendue**:
  - table de mapping widget->endpoint->contrat->fallback.
- **Dependencies**: TV4-UI-01

##### TV-ADV-01-D1 - Dev API client layer
- **Owner**: dev
- **Objectif**: créer un client API frontend centralisé.
- **Scope IN**:
  - helper unique `fetchJson` (timeout, parse error, retry léger)
  - normalisation format retour (`ok`, `data`, `error`, `source`)
- **Scope OUT**: branchement de tous les widgets.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Normaliser strictement la shape `ok/data/error` et remonter les champs utiles sans les renommer (éviter des adapters widget-spécifiques).
  - Respecter le contrat backend "never-empty": si `ok=true` mais `data` partiel, l'UI doit afficher un état `degraded` plutôt que casser.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - vérification console navigateur sans erreur bloquante.
- **Dependencies**: TV-ADV-01-P

##### TV-ADV-01-D2 - Dev runtime wiring on priority widgets
- **Owner**: dev
- **Objectif**: brancher les widgets MVP prioritaires aux appels backend réels.
- **Scope IN**:
  - brancher au minimum:
    - KPI/dashboard (`/api/dashboard/kpis`)
    - forecasts (`/api/forecasts`)
    - news (`/api/news/feed`)
    - recommendations/brief (`/api/recommendations/daily` ou endpoint validé)
  - conserver fallback explicite quand endpoint indisponible
- **Scope OUT**: migration de tous les widgets secondaires.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/index.html`
  - `copilot-app/frontend/app/mockData.js` (désactivation partielle ciblée)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser les widgets déjà présents: `kpi-cards-pro.html`, `forecast-scenarios.html`, `news-feed.html` (pas de nouveaux layouts).
  - Garder un fallback explicite par widget (badge + message) au lieu de masquer silencieusement les erreurs (pattern Judge: `warnings[]` + `source[]`).
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - validation manuelle `http://localhost:5173`.
- **Dependencies**: TV-ADV-01-D1

##### TV-ADV-01-T1 - Tester contract and runtime checks
- **Owner**: tester
- **Objectif**: valider que le frontend n’est plus mock-driven sur le chemin principal.
- **Scope IN**:
  - vérifier appels réseau réels sur parcours principal
  - vérifier fallback explicite en cas endpoint down
  - vérifier absence de crash UI
- **Scope OUT**: tests e2e exhaustifs multi-pages.
- **Fichiers cibles**:
  - `copilot-app/backend/tests/` (si tests API supplémentaires nécessaires)
  - artefact de preuve dans `finance-app/openclaw-gates/`
- **Evidence attendue**:
  - capture réseau (endpoints réellement appelés),
  - liste erreurs console (attendu: aucune bloquante),
  - preuve fallback visible.
- **Dependencies**: TV-ADV-01-D2

##### TV-ADV-01-QA1 - QA signoff gate
- **Owner**: qa
- **Objectif**: signer PASS/BLOCKED de la migration `TV-ADV-01`.
- **Scope IN**:
  - valider DoD: chemin principal backend-driven + fallback explicite + stabilité UI
  - produire verdict avec blocker explicite si incomplet
- **Scope OUT**: optimisation UX/design.
- **Commandes de gate**:
  - `bash scripts/backend_regression_gate.sh --no-live`
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/tv-adv-01-<timestamp>.md`
- **Sortie obligatoire**:
  - `VERDICT: PASS|BLOCKED`
  - `BLOCKER_ID: NONE|...`
  - `NEXT_ACTION_UNIQUE: ...`
- **Dependencies**: TV-ADV-01-T1

### TV-ADV-02 - Judge widget real wiring
- **Epic**: Epic 3 - Multi-Model Consensus and Judge
- **Objectif**: connecter le widget Judge à des endpoints réels.
- **Scope IN**:
  - utiliser `/api/llm/judge/run` + `/api/llm/providers/working`
  - afficher consensus, modèles utilisés, confiance, conflit éventuel
- **Scope OUT**: redesign du widget.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/components/widgets/llm-judge.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser le backend existant plutôt que créer un nouvel endpoint: `/api/llm/judge/run` (run) + `/api/llm/providers/working` (inventaire g4f).
  - S'inspirer du contrat typé Judge (`schemas/judge.py` + `services/judge_builder.py`) si on doit stabiliser les champs affichés côté UI.
  - Remplacer les étapes statiques "GPT-5/Claude/Gemini" par un rendu data-driven (afficher `model/provider` réellement utilisés et la provenance `source[]/fallback`).
- **Acceptation testable**:
  - question judge déclenche un appel API réel et affiche la réponse runtime.
- **Dependencies**: TV-ADV-01

#### Breakdown for `TV-ADV-02` (UI impact first)

##### TV-ADV-02-P - Planner contract and UX states
- **Owner**: planner
- **Objectif**: verrouiller le contrat UI Judge et les états visuels.
- **Scope IN**:
  - définir les états obligatoires: `idle`, `loading`, `success`, `conflict`, `error`, `fallback`
  - mapper les champs API aux zones UI (consensus, confidence, model list, rationale)
- **Scope OUT**: implémentation JS.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/components/widgets/llm-judge.html`
  - `copilot-app/frontend/app/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Calquer les états sur Judge API: `debug=false` nominal (cache/fast) vs `debug=true` (traces) et exposer `fallback_used` si présent.
  - Garder le contrat minimal: `consensus`, `confidence`, `models[]`, `reasons[]`, `warnings[]`, `source[]`.
- **Evidence attendue**:
  - table `field -> widget slot -> fallback`.
- **Dependencies**: TV-ADV-01-D2

##### TV-ADV-02-D1 - Dev API call integration
- **Owner**: dev
- **Objectif**: brancher le trigger Judge sur endpoints backend réels.
- **Scope IN**:
  - appel principal `/api/llm/judge/run`
  - appel secondaire `/api/llm/providers/working` pour afficher les providers actifs
  - timeout + erreur réseau + retry léger
- **Scope OUT**: optimisation scoring backend.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Utiliser `fetchJson` (TV-ADV-01-D1) pour tous les calls, sans exception.
  - Logger en debug uniquement (console) les champs `model/provider` et `source[]` pour faciliter le support sans bruit en nominal.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - test manuel widget Judge.
- **Dependencies**: TV-ADV-02-P

##### TV-ADV-02-D2 - Dev visual result rendering
- **Owner**: dev
- **Objectif**: rendre la sortie Judge clairement actionnable dans l’UI.
- **Scope IN**:
  - afficher: consensus, confidence, modèles consultés, raisons clés, conflits éventuels
  - afficher badge `runtime`/`fallback` visible
- **Scope OUT**: redesign du layout global.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/components/widgets/llm-judge.html`
  - `copilot-app/frontend/app/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser la structure DOM existante (`#judgeQuestion`, `#judgeProcessing`, `#judgeResult`) et enrichir le rendu, pas de nouveau widget.
  - Afficher un badge explicite `runtime|fallback` en se basant sur `source[]` et/ou `warnings[]` (pattern Judge).
- **Commandes de test**:
  - parcours manuel + screenshot avant/après.
- **Dependencies**: TV-ADV-02-D1

##### TV-ADV-02-T1 - Tester runtime validation
- **Owner**: tester
- **Objectif**: valider le comportement réel du Judge côté UI.
- **Scope IN**:
  - vérification réseau: endpoint Judge réellement appelé
  - vérification UI states: loading/success/error/fallback
  - vérification absence de blocage JS
- **Scope OUT**: test cross-browser complet.
- **Evidence attendue**:
  - capture réseau + captures UI des états critiques.
- **Dependencies**: TV-ADV-02-D2

##### TV-ADV-02-QA1 - QA signoff
- **Owner**: qa
- **Objectif**: valider que le Judge UI apporte un résultat concret utilisateur.
- **Scope IN**:
  - check actionnabilité: un verdict compréhensible + confiance + raison
  - check robustesse: erreur/fallback explicitement visibles
- **Commandes de gate**:
  - `bash scripts/backend_regression_gate.sh --no-live`
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/tv-adv-02-<timestamp>.md`
- **Sortie obligatoire**:
  - `VERDICT: PASS|BLOCKED`
  - `BLOCKER_ID: NONE|...`
  - `NEXT_ACTION_UNIQUE: ...`
- **Dependencies**: TV-ADV-02-T1

### TV-ADV-03 - Refresh data real path
- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: faire de `refreshData()` un refresh réel (pas simulation).
- **Scope IN**:
  - exécuter des refresh fetch sur endpoints clés
  - mettre à jour `last-updated` avec timestamp backend
- **Scope OUT**: scheduler avancé.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
- **Acceptation testable**:
  - refresh déclenche des calls API et reflète l’état `fresh/stale/degraded`.
- **Dependencies**: TV1-FRESH-01, TV-ADV-01

#### Breakdown for `TV-ADV-03` (UI concrete refresh)

##### TV-ADV-03-P - Planner refresh scope lock
- **Owner**: planner
- **Objectif**: définir le périmètre refresh strict pour le flux principal.
- **Scope IN**:
  - lister endpoints minimum à rafraîchir:
    - `/api/dashboard/kpis`
    - `/api/forecasts`
    - `/api/news/feed`
    - endpoint décision principal validé
  - définir règles d’ordre/cadence (debounce/cooldown)
- **Scope OUT**: auto-refresh intelligent avancé.
- **Dependencies**: TV-ADV-01-D2

##### TV-ADV-03-D1 - Dev real refresh orchestration
- **Owner**: dev
- **Objectif**: remplacer la simulation `setTimeout` par un pipeline refresh réel.
- **Scope IN**:
  - refresh parallèle contrôlé des endpoints
  - gestion d’état bouton (loading/success/error)
  - arrêt propre des refresh concurrents
- **Scope OUT**: scheduler background permanent.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - action manuelle bouton refresh.
- **Dependencies**: TV-ADV-03-P

##### TV-ADV-03-D2 - Dev freshness/degraded visual sync
- **Owner**: dev
- **Objectif**: synchroniser le rendu UI avec les métadonnées de fraîcheur.
- **Scope IN**:
  - mettre à jour `.last-updated` depuis timestamps backend
  - rendre explicite `fresh/stale/degraded` après refresh
- **Scope OUT**: système complet de notifications.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/style.css`
- **Dependencies**: TV-ADV-03-D1, TV-ADV-04

##### TV-ADV-03-T1 - Tester refresh flow validation
- **Owner**: tester
- **Objectif**: valider le refresh réel et son impact visible UI.
- **Scope IN**:
  - vérifier appels réseau déclenchés au click
  - vérifier changement visible de timestamps
  - vérifier cas erreur endpoint (degraded visible)
- **Evidence attendue**:
  - capture réseau + captures UI avant/après refresh.
- **Dependencies**: TV-ADV-03-D2

##### TV-ADV-03-QA1 - QA signoff refresh
- **Owner**: qa
- **Objectif**: signer la fiabilité du refresh côté expérience utilisateur.
- **Scope IN**:
  - valider absence de faux “Data refreshed successfully”
  - valider cohérence entre données affichées et état fraîcheur
- **Commandes de gate**:
  - `bash scripts/backend_regression_gate.sh --no-live`
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/tv-adv-03-<timestamp>.md`
- **Sortie obligatoire**:
  - `VERDICT: PASS|BLOCKED`
  - `BLOCKER_ID: NONE|...`
  - `NEXT_ACTION_UNIQUE: ...`
- **Dependencies**: TV-ADV-03-T1

### TV-ADV-04 - Real `/api/freshness` computation
- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: remplacer le placeholder `/api/freshness` par un calcul réel.
- **Scope IN**:
  - calculer les âges depuis snapshots/stores (`forecasts`, `news_feed`, `stocks/prices`, `brief`)
  - retourner SLA verdict exploitable pour gate
- **Scope OUT**: observabilité externe cloud.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/services/snapshot_loader.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser `storage.io.load_json("<key>")` et les helpers timestamp (ex: `_to_utc_iso`) au lieu de chemins absolus.
  - Harmoniser les clés de fraîcheur avec Judge (`generated_at`, `freshness`, `last_update`, `data_timestamps`) pour que le frontend puisse afficher `fresh/stale/degraded` sans logique spéciale.
- **Acceptation testable**:
  - `/api/freshness` ne retourne plus de valeurs statiques codées en dur.
- **Dependencies**: TV1-FRESH-03

### TV-ADV-05 - Persisted copilot history
- **Epic**: Epic 5 - Ask Copilot Deep Analysis
- **Objectif**: supprimer le mock d’historique et persister les conversations.
- **Scope IN**:
  - stocker l’historique minimal des Q/A + métadonnées sources
  - `GET /api/copilot/history` renvoie données persistées
- **Scope OUT**: système complet de sessions multi-utilisateur.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/research/versioned_notes.py` (ou storage dédié)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser le pattern "never-empty + source[] + generated_at" (Judge) pour éviter de casser le frontend quand l'historique est vide.
  - Stockage: préférer une solution déjà présente (ex: `versioned_notes.py` ou `storage.io`) plutôt qu'une nouvelle DB.
- **Acceptation testable**:
  - plus de `mock_conv_*` dans la réponse normale.
- **Dependencies**: TV5-ASK-01

### TV-ADV-06 - KPI endpoint consolidation
- **Epic**: Tech quality enabler
- **Objectif**: éliminer la duplication de logique KPI.
- **Scope IN**:
  - choisir une source unique pour `/api/dashboard/kpis`
  - documenter et aligner le contrat payload
- **Scope OUT**: refonte complète des autres routes dashboard.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/routes/dashboard.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser un seul module (source of truth) et faire pointer l'autre vers lui (import/adapter), plutôt que maintenir 2 implémentations divergentes.
  - Garder l'enveloppe `ok/data` et exposer `generated_at` + `source[]` pour que l'UI puisse tracer l'origine (pattern Judge).
- **Acceptation testable**:
  - un seul chemin de vérité pour KPI, sans divergence de contrat.
- **Dependencies**: TV-ADV-01

### TV-ADV-07 - Decision brief aggregator endpoint
- **Epic**: Epic 4 + Epic 3 bridge
- **Objectif**: exposer un endpoint unique “quoi faire aujourd’hui”.
- **Scope IN**:
  - créer `/api/decision/brief` (ou équivalent) combinant:
    - signaux
    - top risques
    - contexte
    - action résumée
- **Scope OUT**: moteur stratégique long-terme.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py` ou `copilot-app/backend/src/api/routes/recommendations.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser les briques existantes au lieu d'appeler des providers LLM directement:
    - signaux/forecasts existants,
    - `GET /api/news/feed` normalisé,
    - Judge (`GET /api/judge` ou `POST /api/llm/judge/run` selon contrat UI).
  - Structurer la réponse comme Judge: `action`, `confidence`, `why[]`, `risks[]`, `source[]`, `generated_at`, `freshness`, `warnings[]`.
  - Utiliser `core/ticker_normalization.py` pour toute liste de tickers (éviter des alias divergents entre modules).
- **Acceptation testable**:
  - réponse actionnable en un appel pour le frontend 2-3 clics.
- **Dependencies**: TV2-SIGNAL-03, TV3-JUDGE-02

### TV-ADV-08 - API test coverage expansion
- **Epic**: Cross-epic quality gate
- **Objectif**: couvrir endpoints décision non testés.
- **Scope IN**:
  - tests pour:
    - `/api/freshness`
    - `/api/copilot/ask` et `/api/copilot/history`
    - `/api/dashboard/kpis`
    - `/api/intelligence/snapshot`
    - `/api/context/current`
    - `/api/signals/composite`
    - `/api/forecasts`
- **Scope OUT**: test perf massif.
- **Fichiers cibles**:
  - `copilot-app/backend/tests/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Standardiser les assertions shape via le pattern Judge: vérifier `ok`, `data`, `generated_at`, `source[]`, et accepter `warnings[]` sans fail.
  - Garder les tests offline-friendly (pas d'appels externes requis).
- **Acceptation testable**:
  - nouvelles suites passent et protègent les contrats principaux.
- **Dependencies**: TV-ADV-04, TV-ADV-05, TV-ADV-06, TV-ADV-07

### TV-ADV-09 - Deprecation cleanup pack
- **Epic**: Tech quality enabler
- **Objectif**: réduire warnings de dépréciation qui masquent les vrais risques.
- **Scope IN**:
  - migration `@app.on_event` -> lifespan
  - migration `datetime.utcnow()` -> timezone-aware UTC
  - migration pydantic v1 (`@validator`, `max_items`, `Field(...example=...)`)
- **Scope OUT**: migration framework majeure.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/services/judge_pipeline.py`
  - `copilot-app/backend/src/schemas/judge.py`
  - `copilot-app/backend/src/api/routes/portfolios.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Préserver le contrat Judge (schémas + builder) pendant la migration: aucune rename de champs sans alias + tests.
  - Réutiliser les shims de compat déjà présents dans `schemas/judge.py` (v1/v2) et faire des changements incrémentaux pour éviter de casser l'environnement runtime.
- **Acceptation testable**:
  - forte baisse des warnings sur `backend_regression_gate --no-live`.
- **Dependencies**: TV-ADV-08

### TV-ADV-10 - Delivery gate upgrade for decision workflow
- **Epic**: Cross-epic quality gate
- **Objectif**: faire échouer la livraison si le workflow décision n’est pas démontré.
- **Scope IN**:
  - enrichir `run_delivery_gate.sh` avec checks:
    - freshness SLA
    - coverage SLA
    - evidence frontend parcours 2-3 clics
- **Scope OUT**: CI/CD cloud complet.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `docs/scrum/sprint-next.md`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Réutiliser les mêmes métriques que les endpoints exposent déjà (`freshness`, `source[]`, `warnings[]`) plutôt que recalculer dans le gate.
  - Exiger une preuve UI liée aux endpoints réels (Judge/Signals/News/Forecasts), pas une capture d'un état mock.
- **Acceptation testable**:
  - gate bloque explicitement si métriques vision non atteintes.
- **Dependencies**: TV-QA-01, TV-ADV-08

## Changelog (advance tasks)
- 2026-02-26 America/New_York - Added code-audit advance task pack for missing runtime wiring, placeholder removal, tests, and tech debt cleanup.

## Full Epic Decomposition - All Epics (UI-first acceleration)

This section completes the task breakdown for Epic 1 to Epic 6 with dispatch-ready IDs.

Execution lens:
- Prioritize tasks that produce visible UI decision value first.
- Keep runtime cost low (g4f/free providers first, fallback explicit).
- Keep each task in 2-4h execution slices with evidence.

Task ID policy:
- One task = one unique ID.
- Headings that start with `T-` or `TV` are reserved for real tasks only.
- Delta/breakdown/notes headings must not start with a task ID.
- Validation command:
  - `sed -nE 's/^#{2,6}[[:space:]]+((T-[A-Z0-9.]+|TV[0-9A-Z-]+)).*/\1/p' docs/planning/tasks.md | sort | uniq -cd`
  - expected output: empty (no duplicate IDs).

UI-first dispatch lane (recommended order):
1. `TV-ADV-01-D2`
2. `TV-ADV-02-D1`
3. `TV-ADV-02-D2`
4. `TV-ADV-03-D1`
5. `TV-ADV-03-D2`
6. `TV-ADV-07`
7. `TV3-JUDGE-04`
8. `TV4-UI-04`
9. `TV5-ASK-03`
10. `TV6-PORT-04`

### Epic 1 - Data Freshness and Signal Reliability Foundation

#### TV1-FRESH-04 - Freshness reason contract
- **Epic**: Epic 1
- **Priority**: P0
- **Objectif**: exposer le `why stale` pour chaque surface clé.
- **Scope IN**:
  - ajouter `stale_reason` et `source_status` sur prices/news/forecasts
  - harmoniser les valeurs (`fresh`, `stale`, `degraded`)
- **Scope OUT**: monitoring externe.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/routes/forecasts.py`
- **Acceptation testable**:
  - aucun endpoint clé sans `freshness_status` + `stale_reason`.
- **Dependencies**: TV1-FRESH-02

#### TV1-FRESH-05 - Frontend freshness bar sync
- **Epic**: Epic 1
- **Priority**: P0
- **Objectif**: refléter la fraîcheur réelle dans la barre/tiles UI.
- **Scope IN**:
  - lier badges et timestamps aux champs backend
  - fallback visuel explicite si `degraded`
- **Scope OUT**: redesign global.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/style.css`
- **Acceptation testable**:
  - état visuel change correctement entre `fresh/stale/degraded`.
- **Dependencies**: TV1-FRESH-04, TV4-UI-03

#### TV1-FRESH-06 - Freshness regression tests
- **Epic**: Epic 1
- **Priority**: P0
- **Objectif**: verrouiller les contrats de fraîcheur par tests.
- **Scope IN**:
  - tests API pour champs freshness
  - cas stale simulé + cas degraded simulé
- **Scope OUT**: tests de charge.
- **Fichiers cibles**:
  - `copilot-app/backend/tests/`
- **Acceptation testable**:
  - tests freshness passent dans le gate backend.
- **Dependencies**: TV1-FRESH-05

### Epic 2 - Forecast Engine (Asset/Sector)

#### TV2-SIGNAL-04 - Signal rationale enrichment
- **Epic**: Epic 2
- **Priority**: P0
- **Objectif**: fournir `why` (max 3 raisons) et `risk_flag` stables pour chaque signal.
- **Scope IN**:
  - enrichir payload signal avec raisons priorisées
  - normaliser `risk_flag` (`low|medium|high`)
- **Scope OUT**: moteur quant avancé.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/core/`
- **Acceptation testable**:
  - 90%+ des actifs MVP ont `why` non vide et `risk_flag` valide.
- **Dependencies**: TV2-SIGNAL-03

#### TV2-SIGNAL-05 - Horizon calibration rules
- **Epic**: Epic 2
- **Priority**: P0
- **Objectif**: stabiliser short/swing horizon pour éviter signaux incohérents.
- **Scope IN**:
  - règles de cohérence horizon `1-3d` vs `1-2w`
  - fallback neutral explicite en cas conflit de données
- **Scope OUT**: backtesting long terme.
- **Fichiers cibles**:
  - `copilot-app/backend/src/core/`
  - `copilot-app/backend/src/api/main.py`
- **Acceptation testable**:
  - aucun actif sans horizon valide; conflit -> action fallback documentée.
- **Dependencies**: TV2-SIGNAL-04

#### TV2-SIGNAL-06 - Forecast coverage gate
- **Epic**: Epic 2
- **Priority**: P0
- **Objectif**: bloquer la livraison si `Coverage SLA < 90%`.
- **Scope IN**:
  - calcul coverage par cycle sur univers MVP
  - intégrer check coverage dans gate
- **Scope OUT**: dashboard BI externe.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- **Acceptation testable**:
  - gate fail explicite si couverture insuffisante.
- **Dependencies**: TV2-SIGNAL-05, TV-ADV-10

### Epic 3 - Multi-Model Consensus and Judge

#### TV3-JUDGE-01 - Multi-provider opinion collector
- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: collecter au moins 3 avis modèles à coût minimal.
- **Scope IN**:
  - g4f/free providers d’abord
  - format opinion normalisé (`direction`, `confidence`, `rationale`)
- **Scope OUT**: premium provider obligatoire.
- **Fichiers cibles**:
  - `copilot-app/backend/src/services/judge_pipeline.py`
  - `copilot-app/backend/src/api/main.py`
- **Acceptation testable**:
  - endpoint Judge inclut liste des avis collectés.
- **Dependencies**: TV2-SIGNAL-03

#### TV3-JUDGE-02 - Judge arbitration contract
- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: produire un verdict unique stable pour le frontend.
- **Scope IN**:
  - contrat `final_action`, `confidence`, `conflict_mode`, `risk_note`
  - règles d’arbitrage déterministes
- **Scope OUT**: optimisation du modèle lui-même.
- **Fichiers cibles**:
  - `copilot-app/backend/src/services/judge_pipeline.py`
  - `copilot-app/backend/src/schemas/judge.py`
- **Acceptation testable**:
  - shape Judge identique sur runs successifs.
- **Dependencies**: TV3-JUDGE-01

#### TV3-JUDGE-03 - Conflict penalty policy
- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: réduire la confiance quand les modèles divergent.
- **Scope IN**:
  - politique explicite de pénalité confiance
  - marquage `conflict_mode=true` quand divergence forte
- **Scope OUT**: calibration financière avancée.
- **Fichiers cibles**:
  - `copilot-app/backend/src/services/judge_pipeline.py`
- **Acceptation testable**:
  - cas de divergence testés avec baisse de confiance attendue.
- **Dependencies**: TV3-JUDGE-02

#### TV3-JUDGE-04 - Judge decision card integration
- **Epic**: Epic 3
- **Priority**: P0 (UI)
- **Objectif**: afficher le verdict Judge dans la carte décision principale.
- **Scope IN**:
  - afficher action finale + confiance + conflit + raisons
  - badge `runtime`/`fallback` visible
- **Scope OUT**: redesign de toutes les cartes.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/components/widgets/llm-judge.html`
- **Acceptation testable**:
  - utilisateur voit un verdict Judge actionnable sans ouvrir la console.
- **Dependencies**: TV-ADV-02-D2, TV3-JUDGE-03

#### TV3-JUDGE-05 - Cost guardrails and provider fallback
- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: garder un coût proche de zéro en cas de provider instable.
- **Scope IN**:
  - routage prioritaire providers gratuits
  - fallback provider chain + timeout budget
- **Scope OUT**: observabilité cloud des coûts.
- **Fichiers cibles**:
  - `copilot-app/backend/src/services/judge_pipeline.py`
  - `copilot-app/backend/src/api/main.py`
- **Acceptation testable**:
  - Judge répond même avec providers partiellement indisponibles.
- **Dependencies**: TV3-JUDGE-03

#### TV3-JUDGE-06 - Judge quality gate pack
- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: couvrir Judge via tests et gate dédié.
- **Scope IN**:
  - tests contract + conflict + fallback provider
  - artefact QA PASS/BLOCKED dédié
- **Scope OUT**: benchmark massif.
- **Fichiers cibles**:
  - `copilot-app/backend/tests/`
  - `scripts/run_delivery_gate.sh`
- **Acceptation testable**:
  - suites Judge vertes + verdict QA explicite.
- **Dependencies**: TV3-JUDGE-05, TV3-JUDGE-04

### Epic 4 - Decision Cockpit Frontend (2-3 Click Workflow)

#### TV4-UI-04 - Today decision brief screen
- **Epic**: Epic 4
- **Priority**: P1 (UI)
- **Objectif**: écran unique "quoi faire aujourd’hui" en 2-3 clics.
- **Scope IN**:
  - regrouper top actions, risques, contexte, freshness
  - CTA rapides vers actif/secteur
- **Scope OUT**: navigation multi-pages avancée.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/index.html`
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/style.css`
- **Acceptation testable**:
  - flux quotidien complet <=3 clics.
- **Dependencies**: TV-ADV-07, TV-ADV-01-D2

#### TV4-UI-05 - Action panel and quick drill-down
- **Epic**: Epic 4
- **Priority**: P1 (UI)
- **Objectif**: permettre drill-down rapide depuis action globale vers actifs clés.
- **Scope IN**:
  - panneau d’actions priorisées
  - tri par confiance/risque/fraîcheur
- **Scope OUT**: screener avancé.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/style.css`
- **Acceptation testable**:
  - accès au détail d’un actif en 1 clic depuis le brief.
- **Dependencies**: TV4-UI-04

#### TV4-UI-06 - UI performance and caching polish
- **Epic**: Epic 4
- **Priority**: P1
- **Objectif**: rendre l’UI fluide sur refresh fréquent.
- **Scope IN**:
  - cache local léger côté frontend
  - éviter re-renders inutiles sur refresh
- **Scope OUT**: refonte framework.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
- **Acceptation testable**:
  - temps perçu refresh UI réduit sans perte de cohérence.
- **Dependencies**: TV4-UI-05, TV-ADV-03-D1

#### TV4-UI-07 - Mobile sanity for daily flow
- **Epic**: Epic 4
- **Priority**: P1
- **Objectif**: garantir usage mobile basique pour brief quotidien.
- **Scope IN**:
  - vérification responsive des cartes décision
  - correction overflow et lisibilité
- **Scope OUT**: app mobile native.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/style.css`
  - `copilot-app/frontend/app/index.html`
- **Acceptation testable**:
  - parcours quotidien complet sur viewport mobile sans blocage.
- **Dependencies**: TV4-UI-06

### Epic 5 - Ask Copilot Deep Analysis

#### TV5-ASK-01 - Ask contract and orchestrator
- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: stabiliser la réponse ask orientée décision.
- **Scope IN**:
  - contrat réponse: `answer`, `action`, `confidence`, `risk_caveat`, `sources`
  - orchestrer collecte signaux + contexte + judge
- **Scope OUT**: mémoire multi-utilisateur.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/routes/copilot.py`
- **Acceptation testable**:
  - aucune réponse ask sans action + caveat risque.
- **Dependencies**: TV3-JUDGE-02, TV2-SIGNAL-03

#### TV5-ASK-02 - Context pack builder
- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: construire un contexte marché compact et réutilisable.
- **Scope IN**:
  - assembler regime, risques, signaux top, events clés
  - timestamp et fraîcheur explicites dans le contexte
- **Scope OUT**: base vectorielle complète.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/routes/context.py`
- **Acceptation testable**:
  - contexte ask réutilisable et horodaté.
- **Dependencies**: TV5-ASK-01

#### TV5-ASK-03 - Ask UI panel with evidence slots
- **Epic**: Epic 5
- **Priority**: P1 (UI)
- **Objectif**: afficher réponse ask structurée et actionnable côté UI.
- **Scope IN**:
  - zones séparées: action, pourquoi, risques, sources
  - états loading/error/fallback explicites
- **Scope OUT**: chat complet multi-thread.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/index.html`
- **Acceptation testable**:
  - réponse ask lisible sans ouvrir données brutes.
- **Dependencies**: TV5-ASK-02, TV-ADV-05

#### TV5-ASK-04 - Follow-up and history continuity
- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: garder continuité Q/A pour analyse quotidienne.
- **Scope IN**:
  - historique réel (pas mock)
  - follow-up sur la dernière réponse
- **Scope OUT**: auth multi-device.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/frontend/app/app.js`
- **Acceptation testable**:
  - historique persistant visible en UI.
- **Dependencies**: TV5-ASK-03

#### TV5-ASK-05 - Ask latency and cost budget
- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: maintenir ask pratique en quasi temps réel.
- **Scope IN**:
  - timeout budget par étape
  - fallback réponse partielle si provider lent
- **Scope OUT**: infrastructure distribuée.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/services/judge_pipeline.py`
- **Acceptation testable**:
  - ask retourne une réponse utile dans un délai acceptable.
- **Dependencies**: TV5-ASK-04

#### TV5-ASK-06 - Ask quality gate coverage
- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: verrouiller non-régression ask/history.
- **Scope IN**:
  - tests `/api/copilot/ask` + `/api/copilot/history`
  - gate QA avec blocker explicite
- **Scope OUT**: tests charge.
- **Fichiers cibles**:
  - `copilot-app/backend/tests/`
  - `scripts/run_delivery_gate.sh`
- **Acceptation testable**:
  - tests ask/history verts + artefact gate.
- **Dependencies**: TV5-ASK-05

### Epic 6 - Portfolio Adaptation Layer

#### TV6-PORT-01 - Watchlist profile model
- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: créer un profil watchlist personnel exploitable par recommandations.
- **Scope IN**:
  - structure watchlist prioritaire
  - tags secteur/conviction par actif
- **Scope OUT**: multi-utilisateur.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/routes/portfolios.py`
  - `copilot-app/backend/src/schemas/`
- **Acceptation testable**:
  - création/lecture watchlist fonctionnelle via API.
- **Dependencies**: none

#### TV6-PORT-02 - Risk posture settings
- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: ajouter profil `conservative|neutral|aggressive`.
- **Scope IN**:
  - persistance profil de risque
  - exposition API de lecture/écriture
- **Scope OUT**: optimisation quant sophistiquée.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/routes/portfolios.py`
- **Acceptation testable**:
  - changement de posture modifie les paramètres de décision.
- **Dependencies**: TV6-PORT-01

#### TV6-PORT-03 - Portfolio-aware reranking
- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: reclasser actions recommandées selon watchlist + risque.
- **Scope IN**:
  - score de priorité portfolio-aware
  - exposer top actions adaptées via endpoint
- **Scope OUT**: optimisation de position sizing.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/core/`
- **Acceptation testable**:
  - deux profils de risque donnent un top actions différent.
- **Dependencies**: TV6-PORT-02, TV2-SIGNAL-06

#### TV6-PORT-04 - Portfolio action summary card
- **Epic**: Epic 6
- **Priority**: P2 (UI)
- **Objectif**: afficher "ce que je fais aujourd’hui sur mon portefeuille".
- **Scope IN**:
  - carte UI action portfolio (add/hold/reduce)
  - motifs et niveau de risque
- **Scope OUT**: exécution ordre broker.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/index.html`
- **Acceptation testable**:
  - carte visible et cohérente avec profil utilisateur.
- **Dependencies**: TV6-PORT-03, TV4-UI-05

#### TV6-PORT-05 - Daily portfolio digest
- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: générer un résumé quotidien portfolio compact.
- **Scope IN**:
  - endpoint digest quotidien
  - inclusion des variations critiques + actions proposées
- **Scope OUT**: reporting institutionnel.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/routes/portfolios.py`
  - `copilot-app/backend/src/api/main.py`
- **Acceptation testable**:
  - digest disponible en un appel API.
- **Dependencies**: TV6-PORT-04

#### TV6-PORT-06 - Portfolio adaptation QA gate
- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: valider que l’adaptation portefeuille est stable et traçable.
- **Scope IN**:
  - tests API profil/watchlist/reranking/digest
  - gate QA PASS/BLOCKED dédié
- **Scope OUT**: test perfs massifs.
- **Fichiers cibles**:
  - `copilot-app/backend/tests/`
  - `scripts/run_delivery_gate.sh`
- **Acceptation testable**:
  - non-régression validée pour les flux portfolio.
- **Dependencies**: TV6-PORT-05

### Epic 7 - Geopolitical and Macro Impact Radar

#### TV7-MACRO-01 - Geopolitical event ingestion contract
- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: structurer l’entrée des événements géopolitiques impact marché.
- **Scope IN**:
  - contrat `event_type`, `region`, `severity`, `timestamp`, `sources`
  - endpoint d’ingestion/snapshot normalisé
- **Scope OUT**: moteur prédictif complexe.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/routes/context.py`
- **Acceptation testable**:
  - les événements critiques sont exposés via un format stable.
- **Dependencies**: TV1-FRESH-01

#### TV7-MACRO-02 - Event-to-asset impact mapping
- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: relier chaque événement aux actifs/secteurs concernés.
- **Scope IN**:
  - mapping impacts: indices, métaux, secteurs, mega-cap
  - score d’impact `low|medium|high`
- **Scope OUT**: corrélations causales avancées.
- **Fichiers cibles**:
  - `copilot-app/backend/src/core/`
  - `copilot-app/backend/src/api/main.py`
- **Acceptation testable**:
  - un événement retourne une liste d’actifs/secteurs impactés.
- **Dependencies**: TV7-MACRO-01

#### TV7-MACRO-03 - Regime shift flags
- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: signaler rapidement un basculement risk-on/risk-off.
- **Scope IN**:
  - flags `regime_shift`, `risk_mode`, `confidence`
  - intégration au contexte courant (`/api/context/current`)
- **Scope OUT**: modèle macro complet.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/routes/context.py`
  - `copilot-app/backend/src/api/main.py`
- **Acceptation testable**:
  - présence d’un flag de régime exploitable par UI et Ask.
- **Dependencies**: TV7-MACRO-02

#### TV7-MACRO-04 - Macro risk strip in decision UI
- **Epic**: Epic 7
- **Priority**: P2 (UI)
- **Objectif**: afficher les 3 risques macro/géo dominants dans le cockpit.
- **Scope IN**:
  - bandeau risques avec sévérité + timestamp
  - lien direct vers actifs/secteurs impactés
- **Scope OUT**: page macro dédiée complète.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/index.html`
  - `copilot-app/frontend/app/style.css`
- **Acceptation testable**:
  - l’utilisateur voit immédiatement les risques macro utiles à la décision.
- **Dependencies**: TV7-MACRO-03, TV4-UI-04

#### TV7-MACRO-05 - Macro-aware recommendation adjustments
- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: ajuster recommandations en fonction du risque macro actif.
- **Scope IN**:
  - pénaliser les actions agressives en mode risk-off
  - injecter caveat macro dans `decision brief`
- **Scope OUT**: allocation portefeuille automatique.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/core/`
- **Acceptation testable**:
  - changement de régime modifie action/confiance sur le brief.
- **Dependencies**: TV7-MACRO-04, TV-ADV-07

#### TV7-MACRO-06 - Macro radar QA gate
- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: verrouiller la fiabilité du radar macro/géo.
- **Scope IN**:
  - tests API ingestion/mapping/flags
  - gate QA avec preuves UI risk strip
- **Scope OUT**: test perfs large-scale.
- **Fichiers cibles**:
  - `copilot-app/backend/tests/`
  - `scripts/run_delivery_gate.sh`
- **Acceptation testable**:
  - verdict PASS/BLOCKED explicite sur le flux macro.
- **Dependencies**: TV7-MACRO-05

### Epic 8 - Cost Governance and Runtime Efficiency

#### TV8-COST-01 - Provider routing policy (free-first)
- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: forcer un routage low-cost par défaut sur tout flux IA.
- **Scope IN**:
  - ordre de priorité providers gratuits
  - fallback contrôlé vers options payantes seulement si nécessaire
- **Scope OUT**: billing multi-tenant.
- **Fichiers cibles**:
  - `copilot-app/backend/src/services/judge_pipeline.py`
  - `copilot-app/backend/src/api/main.py`
- **Acceptation testable**:
  - appels IA passent d’abord par la chaîne low-cost.
- **Dependencies**: TV3-JUDGE-05, TV5-ASK-05

#### TV8-COST-02 - Request/token budget metering
- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: mesurer le coût par endpoint critique (Judge/Ask/Brief).
- **Scope IN**:
  - métriques `requests`, `estimated_tokens`, `estimated_cost`
  - export local journalier
- **Scope OUT**: facturation provider réelle.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `scripts/`
- **Acceptation testable**:
  - rapport coût journalier disponible localement.
- **Dependencies**: TV8-COST-01

#### TV8-COST-03 - Timeout and circuit-breaker policy
- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: éviter blocage UX si providers instables.
- **Scope IN**:
  - timeout budget par endpoint
  - circuit-breaker avec fallback réponse partielle
- **Scope OUT**: orchestration distribuée.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/services/judge_pipeline.py`
- **Acceptation testable**:
  - UI reçoit toujours une réponse exploitable, même en dégradé.
- **Dependencies**: TV8-COST-02

#### TV8-COST-04 - Runtime cost/degraded badge in UI
- **Epic**: Epic 8
- **Priority**: P1 (UI)
- **Objectif**: rendre visible l’état runtime/cost pour éviter décisions aveugles.
- **Scope IN**:
  - badge global `runtime_ok | degraded | fallback`
  - indication coût relatif (`low/medium/high`) par réponse IA
- **Scope OUT**: dashboard finance complet.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/style.css`
- **Acceptation testable**:
  - état runtime et niveau coût visibles sans debug console.
- **Dependencies**: TV8-COST-03, TV5-ASK-03

#### TV8-COST-05 - Monthly cost guardrail report
- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: contrôler budget mensuel sans outils externes coûteux.
- **Scope IN**:
  - rapport mensuel local consolidé
  - seuils d’alerte (`soft_limit`, `hard_limit`)
- **Scope OUT**: intégration SaaS FinOps.
- **Fichiers cibles**:
  - `scripts/`
  - `docs/ops/`
- **Acceptation testable**:
  - dépassement seuil remonte alerte explicite.
- **Dependencies**: TV8-COST-04

#### TV8-COST-06 - Cost governance gate
- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: bloquer livraison si contraintes coût/runtime non tenues.
- **Scope IN**:
  - checks coût, fallback rate, timeout rate
  - verdict PASS/BLOCKED dans gate final
- **Scope OUT**: arbitrage business long terme.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- **Acceptation testable**:
  - gate échoue explicitement en cas de dérive coût.
- **Dependencies**: TV8-COST-05, TV-ADV-10

### Epic 9 - Decision Journal and Learning Loop

#### TV9-LOOP-01 - Decision journal schema
- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: définir le format de journal de décision quotidien.
- **Scope IN**:
  - champs `decision_id`, `date`, `action`, `confidence`, `why`, `risk`, `sources`
  - persistance locale simple
- **Scope OUT**: analytics avancées.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/routes/portfolios.py`
  - `copilot-app/backend/src/api/main.py`
- **Acceptation testable**:
  - chaque daily brief peut être enregistré avec ID unique.
- **Dependencies**: TV-ADV-07

#### TV9-LOOP-02 - Auto-capture from daily brief
- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: créer l’entrée journal automatiquement après génération du brief.
- **Scope IN**:
  - hook sur endpoint décision
  - marquage de provenance (`manual` vs `auto`)
- **Scope OUT**: workflow multi-user.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/routes/recommendations.py`
- **Acceptation testable**:
  - une décision quotidienne crée une entrée journal sans action manuelle.
- **Dependencies**: TV9-LOOP-01

#### TV9-LOOP-03 - Outcome tracking (simple P/L proxy)
- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: mesurer ex-post la qualité des décisions.
- **Scope IN**:
  - suivi simple `outcome_1d`, `outcome_1w`
  - statut `good/neutral/bad` basé sur règle explicite
- **Scope OUT**: attribution factorielle complexe.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/core/`
- **Acceptation testable**:
  - chaque entrée journal peut recevoir un outcome court terme.
- **Dependencies**: TV9-LOOP-02, TV2-SIGNAL-05

#### TV9-LOOP-04 - Journal timeline UI
- **Epic**: Epic 9
- **Priority**: P2 (UI)
- **Objectif**: rendre visible l’historique des décisions et outcomes.
- **Scope IN**:
  - timeline décisions (date/action/confiance/outcome)
  - filtre rapide actif/secteur
- **Scope OUT**: dashboard BI complet.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/index.html`
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/style.css`
- **Acceptation testable**:
  - l’utilisateur peut revoir ses décisions passées en 1-2 clics.
- **Dependencies**: TV9-LOOP-03

#### TV9-LOOP-05 - Feedback weighting for next recommendations
- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: ajuster légèrement la confiance future selon historique outcomes.
- **Scope IN**:
  - pondération simple positive/négative
  - trace de l’ajustement dans le brief
- **Scope OUT**: apprentissage ML full auto.
- **Fichiers cibles**:
  - `copilot-app/backend/src/core/`
  - `copilot-app/backend/src/api/main.py`
- **Acceptation testable**:
  - recommendations incluent un ajustement explicable lié au journal.
- **Dependencies**: TV9-LOOP-04

#### TV9-LOOP-06 - Learning loop QA gate
- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: valider la robustesse de la boucle apprentissage décisionnelle.
- **Scope IN**:
  - tests capture/outcome/feedback
  - gate QA avec preuve timeline UI
- **Scope OUT**: validation statistique avancée.
- **Fichiers cibles**:
  - `copilot-app/backend/tests/`
  - `scripts/run_delivery_gate.sh`
- **Acceptation testable**:
  - gate PASS/BLOCKED explicite sur boucle de feedback.
- **Dependencies**: TV9-LOOP-05

## Changelog (all-epics decomposition)
- 2026-02-26 America/New_York - Added complete Epic 1-6 task decomposition with UI-first dispatch lane and explicit dependencies.
- 2026-02-26 America/New_York - Enforced unique task-ID heading policy and removed heading ID collisions in delta/breakdown sections.
- 2026-02-26 America/New_York - Added Epic 7/8/9 tasks: macro-geopolitical radar, cost governance, and decision learning loop.
