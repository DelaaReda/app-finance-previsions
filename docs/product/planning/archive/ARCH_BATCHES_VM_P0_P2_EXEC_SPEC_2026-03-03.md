---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md
  - /home/venom/analyse-financiere/docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md
---

# Batches Architecture VM — P0 → P2 (Execution Spec)

Date: 2026-03-03  
Contexte: migration majeure, exécution cible VM, lancement officiel via `./finance-copilot.sh`

## Principes d’exécution

- Toujours lancer/valider via `./finance-copilot.sh`.
- Aucun mock pour masquer une panne backend; fallback explicite uniquement.
- Chaque batch doit produire une preuve exécutable (commande + sortie attendue).
- Un batch n’est `DONE` que si les critères d’acceptation et les preuves sont complets.

---

## État actuel des batches

- `BATCH-VM-P0-01` — **DONE**  
  Runtime bootstrap unifié (`requirements.runtime.txt` + `bootstrap_backend_env.sh` + preflight deps dans launcher).
- `BATCH-VM-P0-02` — **DONE (2026-03-03)**  
  Correctifs appliqués + validés:
  - bridge namespace `research` vers legacy modules,
  - fallback forecasts (`jobs.forecasts_simple`) dans `validate_and_generate_data.py`,
  - compat annotations runtime dans `news_ingest.py`.
  Vérification:
  - `/api/stocks/SPY/sheet` -> `200`
  - scan logs sans `TypeError`, sans `No module named 'jobs.forecasts'`, sans `No module named 'research.scoring'`.

Les batches ci-dessous sont les prochains à exécuter.

---

## BATCH-VM-P0-02 — Compatibilité Runtime & Import Bridge

Objectif:
Supprimer les crashes/404 causés par imports legacy cassés et incompatibilités Python runtime.

Scope:

- `apps/api/src/platform/legacy/jobs/news_ingest.py`
- `apps/api/src/platform/legacy/jobs/validate_and_generate_data.py`
- `apps/api/src/platform/main.py`
- `apps/api/src/research/` (bridge modules à ajouter)
- `apps/api/src/jobs/` (bridge minimal si requis)

Travaux:

1. Corriger les annotations non compatibles runtime (ex: `datetime | None`) via `Optional[...]` ou `from __future__ import annotations`.
2. Ajouter bridges explicites:
   - `research/scoring.py` -> délégation vers `platform/legacy/research/scoring.py`
   - `research/alerts.py` -> délégation vers `platform/legacy/research/alerts.py`
3. Corriger la génération forecasts dans `validate_and_generate_data.py` (plus d’import `jobs.forecasts` inexistant).
4. Nettoyer les appels jobs introuvables (`judge_quality_report.py`) avec garde stricte + log propre.

Critères d’acceptation:

- `./finance-copilot.sh start` sans `TypeError` dans `news_ingest`.
- `./finance-copilot.sh start` sans `No module named 'jobs.forecasts'`.
- `/api/stocks/SPY/sheet` retourne `200`.

Validation:

```bash
./finance-copilot.sh start
curl -sS -i "http://localhost:8050/api/stocks/SPY/sheet" | head -n 20
grep -E "TypeError|No module named 'jobs.forecasts'" apps/api/runtime/api.log /tmp/data_generation.log || true
./finance-copilot.sh stop
```

Preuve attendue:

- `BATCH_VM_P0_02_PROOF.md` (logs + statuts endpoints).

---

## BATCH-VM-P0-03 — Endpoint Contract Recovery (UI Blocking)

Objectif:
Restaurer les routes attendues par l’UI et aligner les réponses sur un contrat stable.

Scope:

- `apps/api/src/platform/main.py`
- `apps/api/src/domains/market_data/api/*.py`
- `apps/api/src/domains/forecasts/api/*.py`

Travaux:

1. Ajouter/maintenir route compat: `/api/macro/series/latest` (ou alias clair vers route canonique).
2. Garantir le contrat JSON de:
   - `/api/forecasts`
   - `/api/recommendations/daily`
   - `/api/stocks/{ticker}/sheet`
3. Uniformiser `ok/data/error/freshness` (jamais de message brut technique côté payload public).

Critères d’acceptation:

- `/api/macro/series/latest` retourne `200`.
- Les trois endpoints critiques UI ci-dessus retournent `200` + structure stable.
- Zéro 404 fonctionnel sur le parcours dashboard nominal.

Validation:

```bash
./finance-copilot.sh start
curl -sS "http://localhost:8050/api/macro/series/latest" | jq '.ok, .data != null'
curl -sS "http://localhost:8050/api/forecasts?horizon=short&limit=24" | jq '.ok, .data'
curl -sS "http://localhost:8050/api/recommendations/daily?limit=3" | jq '.ok, .data'
curl -sS "http://localhost:8050/api/stocks/SPY/sheet" | jq '.ok, .data.ticker'
./finance-copilot.sh stop
```

Preuve attendue:

- `BATCH_VM_P0_03_CONTRACT_REPORT.json`

---

## BATCH-VM-P1-01 — Startup Critical Path Reduction

Objectif:
Réduire le temps de boot perçu sans perdre la qualité data.

Baseline audit:

- Cold start mesuré: `~41.34s`.

Scope:

- `apps/api/runtime/copilot.sh`
- jobs ingestion/refresh concernés dans `apps/api/src/platform/legacy/jobs/`

Travaux:

1. Déplacer les jobs lourds non bloquants hors chemin critique (`start` -> async post-ready).
2. Conserver seulement les prérequis stricts avant “backend up”.
3. Ajouter mode `start --fast` (optionnel) pour QA/dev loops.
4. Instrumenter timings startup (phase-by-phase) dans logs.

Critères d’acceptation:

- `time ./finance-copilot.sh start` <= `20s` (cible P1).
- Backend santé disponible avant refresh complet.
- Aucune régression sur endpoints core.

Validation:

```bash
/usr/bin/time -p ./finance-copilot.sh start
curl -sS "http://localhost:8050/api/health" | jq .
./finance-copilot.sh stop
```

Preuve attendue:

- `BATCH_VM_P1_01_STARTUP_TIMING.md` (avant/après).

---

## BATCH-VM-P1-02 — Monolith Route De-Risk (main.py)

Objectif:
Réduire le risque de régression lié au monolithe `platform/main.py` (5244 lignes).

Scope:

- `apps/api/src/platform/main.py`
- `apps/api/src/domains/*/api/*.py`
- `apps/api/src/platform/routes/__init__.py`

Travaux:

1. Identifier endpoints dupliqués entre monolithe et domain routers.
2. Déclarer “source de vérité” par endpoint.
3. Conserver wrappers de compat minces, déplacer logique métier vers `domains/*/application`.
4. Marquer explicitement les routes legacy dépréciées.

Critères d’acceptation:

- Réduction nette du code endpoint directement dans `main.py`.
- Plus de duplication active pour les routes P0.
- Tests de non-régression API passants.

Validation:

```bash
python3 -m pytest -q apps/api/src/domains
python3 - <<'PY'
from pathlib import Path
import re
p = Path('apps/api/src/platform/main.py').read_text()
print('app_get_count=', len(re.findall(r'@app\\.get\\(', p)))
PY
```

Preuve attendue:

- `BATCH_VM_P1_02_ROUTE_OWNERSHIP.md`

---

## BATCH-VM-P1-03 — Forecast Data Reliability & Freshness

Objectif:
Empêcher les sections UI “vides silencieuses” en garantissant un flux forecasts exploitable ou un fallback explicite.

Scope:

- `apps/api/src/domains/forecasts/application/*.py`
- `apps/api/src/platform/legacy/jobs/forecasts_simple.py`
- `apps/api/src/platform/legacy/jobs/validate_and_generate_data.py`

Travaux:

1. Fiabiliser pipeline forecasts lors du bootstrap.
2. Ajouter statut fraîcheur clair (`fresh/stale/unknown`) uniformisé.
3. Encadrer le fallback: jamais faux-positif, jamais crash.

Critères d’acceptation:

- `/api/forecasts` retourne une structure cohérente même en absence de données.
- `/api/recommendations/daily` cohérent avec disponibilité forecasts.
- Trace fraîcheur présente et exploitable.

Validation:

```bash
./finance-copilot.sh start
curl -sS "http://localhost:8050/api/forecasts?horizon=short&limit=24" | jq '.ok, .data.freshness_status, .data.count'
curl -sS "http://localhost:8050/api/recommendations/daily?limit=3" | jq '.ok, .data.generated_at'
./finance-copilot.sh stop
```

Preuve attendue:

- `BATCH_VM_P1_03_FORECAST_RELIABILITY.md`

---

## BATCH-VM-P2-01 — Observabilité Contractuelle API

Objectif:
Disposer d’un tableau de bord technique minimal pour détecter immédiatement les ruptures de contrat.

Scope:

- `apps/api/src/platform/main.py`
- `apps/monitor/` (si utilisé)
- `docs/ops/` (runbook)

Travaux:

1. Exposer endpoint interne de “contract health” (liste endpoints critiques + status).
2. Ajouter checks auto au démarrage et en cron.
3. Publier runbook incident (triage endpoint KO).

Critères d’acceptation:

- Un seul endpoint donne l’état de santé des contrats critiques.
- Détection claire des 404/500 contractuels.

Validation:

```bash
curl -sS "http://localhost:8050/api/health"
curl -sS "http://localhost:8050/api/contract/health" | jq .
```

Preuve attendue:

- `BATCH_VM_P2_01_CONTRACT_HEALTH_PROOF.json`

---

## BATCH-VM-P2-02 — Cross-Environment Determinism (VM-first)

Objectif:
Garantir que la même commande produit le même résultat, indépendamment du shell/session.

Scope:

- `apps/api/runtime/copilot.sh`
- `apps/api/runtime/bootstrap_backend_env.sh`
- `apps/api/src/requirements.runtime.txt`
- docs runbook runtime

Travaux:

1. Verrouiller version/runtime policy Python.
2. Ajouter preflight exhaustif (deps, imports bridges, data dirs).
3. Stabiliser logs “machine-readable” pour debug agentique.

Critères d’acceptation:

- `start/status/stop` déterministes.
- Zéro erreur d’import inattendue dans les logs startup.

Validation:

```bash
./apps/api/runtime/bootstrap_backend_env.sh
./finance-copilot.sh start
./finance-copilot.sh status
./finance-copilot.sh stop
```

Preuve attendue:

- `BATCH_VM_P2_02_RUNTIME_DETERMINISM.md`

---

## Ordre d’exécution recommandé

1. `BATCH-VM-P0-03`
2. `BATCH-VM-P1-01`
3. `BATCH-VM-P1-02`
4. `BATCH-VM-P1-03`
5. `BATCH-VM-P2-01`
6. `BATCH-VM-P2-02`

Règle de passage:

- Aucun batch suivant si un batch précédent laisse un endpoint critique en 404/500.
