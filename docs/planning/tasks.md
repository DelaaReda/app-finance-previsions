# Tasks détaillées orientées exécution par agents qwen

## Convention de dispatch
- **Rôles qwen**: planner, dev, tester, qa
- **Taille cible**: 2-4h / tâche
- **Format sortie obligatoire**: DELTA / EVIDENCE / RISKS / NEXT

---

## T-A1.1 — Verrouiller contrat `/api/health`
- **Objectif**: réponse health stable et rétro-compatible.
- **Scope IN**: normalisation shape + tests.
- **Scope OUT**: ajout observabilité avancée.
- **Prérequis**: backend bootable.
- **Fichiers cibles**: `copilot-app/backend/src/api/main.py`, `copilot-app/backend/tests/test_health.py`
- **Plan implémentation**:
  1. Définir schéma attendu (top-level + data).
  2. Harmoniser champs `status`.
  3. Ajuster/ajouter tests.
- **Critères d’acceptation testables**:
  - Endpoint renvoie 200 + `ok=true`.
  - `data.timestamp` présent.
- **Commandes de test**:
  - `curl -sS http://localhost:8050/api/health | jq`
  - `cd copilot-app/backend && .venv/bin/pytest -q tests/test_health.py`
- **Evidences attendues**: payload health + pytest vert.
- **Risques**: clients dépendants anciens champs.
- **Dépendances**: aucune.

## T-A2.1 — Unifier réponse mono ticker `/api/stocks/prices`
- **Objectif**: contrat UI-friendly pour 1 ticker.
- **Scope IN**: champs `ticker, points, count, timestamp`.
- **Scope OUT**: provider data externe.
- **Prérequis**: snapshot `stocks/prices` ou fallback actif.
- **Fichiers cibles**: `copilot-app/backend/src/api/main.py`
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
- **Plan implémentation**:
  1. Ajouter tests `tickers=SPY,QQQ`.
  2. Ajouter test paramètre manquant.
- **Critères d’acceptation testables**:
  - Tests passent.
  - Aucun 500 en cas input incomplet.
- **Commandes de test**:
  - `cd copilot-app/backend && .venv/bin/pytest -q tests/test_stocks_prices_contract.py`
- **Evidences attendues**: rapport pytest.
- **Risques**: divergence selon fixtures data.
- **Dépendances**: T-A2.1.

## T-A3.1 — Normaliser `news_feed` items
- **Objectif**: items news exploitables et homogènes.
- **Scope IN**: mapping title/url/source/date/tickers/score.
- **Scope OUT**: scoring algorithmique news.
- **Prérequis**: endpoint existant.
- **Fichiers cibles**: `copilot-app/backend/src/api/main.py`, `copilot-app/backend/src/api/services/news_service.py`
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
- **Plan implémentation**:
  1. Ecrire tests nominal + edge cases.
  2. Valider non-régression.
- **Critères d’acceptation testables**:
  - pytest vert.
- **Commandes de test**:
  - `cd copilot-app/backend && .venv/bin/pytest -q tests/test_news_feed_contract.py`
- **Evidences attendues**: rapport pytest.
- **Risques**: dépendance aux fixtures runtime.
- **Dépendances**: T-A3.1.

## T-A4.1 — Confirmer route unique `/api/forecasts`
- **Objectif**: éviter ambiguïtés d’implémentation forecasts.
- **Scope IN**: route active unique via router.
- **Scope OUT**: calcul des scores forecast.
- **Prérequis**: boot backend OK.
- **Fichiers cibles**: `copilot-app/backend/src/api/main.py`, `copilot-app/backend/src/api/routes/forecasts.py`
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
- **Dépendances**: A1..A5, B1..B2.

## T-C1.2 — Runbook qwen orchestration MVP
- **Objectif**: standardiser dispatch/monitoring des tâches.
- **Scope IN**: prompts par rôle, cadence check, format preuves.
- **Scope OUT**: auto-remédiation complète.
- **Prérequis**: orchestrator opérationnel.
- **Fichiers cibles**: `docs/planning/mvp-plan.md`, `docs/planning/tasks.md`, `scripts/qwen_orchestrator.py` (si nécessaire)
- **Plan implémentation**:
  1. Définir commandes standards dispatch.
  2. Définir fréquence check run artifacts.
  3. Ajouter section BLOCKED handling.
- **Critères d’acceptation testables**:
  - Un run complet produit `transcript.md`, `events.jsonl`, `agent_activity.json`.
- **Commandes de test**:
  - `python3 scripts/qwen_orchestrator.py --tmux-cmd status`
  - `python3 scripts/analyze_orchestrator_runs.py --runs-dir finance-app/orchestrator-runs --limit 3`
- **Evidences attendues**: résumé exécution + run_id auditable.
- **Risques**: saturation context/token selon prompts.
- **Dépendances**: T-C1.1.

---

## Pack de dispatch qwen (delta incrémental)

### Batch-01
- **Tâches**: `T-A1.1`, `T-A2.1`
- **Instruction commune agents**:
  - livrer strictement le scope IN
  - joindre commandes exactes exécutées
  - joindre preuves minimales (payload JSON + sortie tests)
  - terminer avec verdict `PASS` ou `BLOCKED` motivé
- **Blocage immédiat si**:
  - absence de section EVIDENCE
  - test non exécuté
  - contrat API modifié sans test mis à jour
- **Chemin artefact obligatoire**:
  - `finance-app/openclaw-gates/batch-01-<timestamp>.md`
  - contenu minimal: `DELTA`, `EVIDENCE`, `RISKS`, `NEXT`, `VERDICT`

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

## Delta tâches qwen (cycle 20:20)

### T-A1.1 — commandes de test renforcées
- Ajouter boucle stabilité:
  - `for i in {1..3}; do curl -sS http://localhost:8050/api/health | jq -c '{ok,status,ts:.data.timestamp}'; done`
- Critère additionnel: 3/3 réponses exploitables, sans clé absente.

### T-A2.1 — commandes de test renforcées
- Ajouter vérification robuste des clés:
  - `for i in {1..5}; do curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq -c '{ok,ticker,count,has_points:(.data.points!=null),has_ts:(.data.timestamp!=null)}'; done`
- Critère additionnel: 5/5 réponses sans erreur serveur.

### Template d’évidence obligatoire (toutes tâches Batch-01)
```text
DELTA:
EVIDENCE:
- cmd:
  output:
RISKS:
NEXT:
VERDICT: PASS|BLOCKED
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

#### T-A2.2 — carte d’assignation prête
```text
[TASK_ID] T-A2.2
OBJECTIF: valider contrat multi-ticker /api/stocks/prices
SCOPE_IN: tests tickers=SPY,QQQ; test input incomplet; absence de 500
SCOPE_OUT: optimisation perf; refactor endpoint
PREREQUIS: VERDICT PASS Batch-01
FICHIERS_CIBLES: copilot-app/backend/tests/test_stocks_prices_contract.py
PLAN_IMPLEMENTATION: écrire tests -> exécuter -> corriger si rouge -> re-run vert
ACCEPTANCE_TESTABLE: pytest vert; map multi-ticker stable; cas incomplet non bloquant
COMMANDES_TEST: cd copilot-app/backend && .venv/bin/pytest -q tests/test_stocks_prices_contract.py
EVIDENCES_ATTENDUES: sortie pytest + payload multi-ticker de référence
RISQUES: fixtures data divergentes
DEPENDANCES: T-A2.1
VERDICT_ATTENDU: PASS|BLOCKED
```

#### T-A3.1 — carte d’assignation prête
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

## Changelog
- 2026-02-24 19:50 America/New_York — Ajout du pack de dispatch qwen Batch-01 avec règles de preuve et conditions de blocage immédiat.
- 2026-02-24 20:05 America/New_York — Ajout du chemin d’artefact obligatoire pour Batch-01 et d’une checklist QA de handoff pour fiabiliser le verdict.
- 2026-02-24 20:20 America/New_York — Renforcement incrémental des tâches Batch-01 (boucles de stabilité health/stocks) + template d’évidence unifié PASS/BLOCKED.
- 2026-02-24 20:35 America/New_York — Ajout d’un runbook de lot (Batch-01 immédiat, Batch-02 conditionnel), règle d’activation explicite via artefact gate, et template d’assignation standardisé pour agents qwen.
- 2026-02-24 20:50 America/New_York — Préparation du pack Batch-02 avec cartes d’assignation complètes pour T-A2.2/T-A3.1 et règle de séquencement bloquant.
