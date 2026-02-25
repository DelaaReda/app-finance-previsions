# Epics MVP — orientées exécution agents qwen

## EPIC A — Stabiliser les contrats API MVP

### Objectif
Garantir des réponses cohérentes, testables et stables sur les 5 endpoints MVP.

### Scope IN
- Normalisation payload succès/erreur
- Vérification de la cohérence route vs router (`/api/forecasts`)
- Ajout/renforcement tests backend ciblés MVP

### Scope OUT
- Refonte complète architecture backend
- Ajout de nouvelles familles d’endpoints non MVP

### Prérequis
- Backend local démarrable (`./finance-copilot.sh restart`)
- `.venv` backend opérationnel

### Fichiers cibles
- `copilot-app/backend/src/api/main.py`
- `copilot-app/backend/src/api/routes/forecasts.py`
- `copilot-app/backend/tests/test_health.py`
- `copilot-app/backend/tests/` (nouveaux tests endpoint)

### Dépendances
- EPIC C (quality gate) pour verrouillage final

### Risques
- Régressions liées aux fallbacks historiques
- Variabilité des données snapshots

### Critères d’acceptation testables
1. Les 5 endpoints MVP retournent HTTP 200 en mode nominal.
2. Chaque endpoint retourne un objet top-level avec `ok` + charge utile structurée.
3. Pas d’erreur 500 sur 10 appels successifs à chaque endpoint.
4. Tests backend MVP passent en local.

### Commandes de test
```bash
curl -sS http://localhost:8050/api/health | jq
curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq
curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq
curl -sS "http://localhost:8050/api/forecasts" | jq
curl -sS -X POST "http://localhost:8050/api/copilot/ask" -H 'Content-Type: application/json' \
  -d '{"question":"Vue rapide du marché","max_sources":3}' | jq
cd copilot-app/backend && .venv/bin/pytest -q
```

### Evidences attendues
- Sorties `curl|jq` sauvegardables
- Log `api.log` sans tracebacks critiques
- Rapport pytest vert

---

## EPIC B — Intégrer le frontend MVP avec données réelles

### Objectif
Rendre l’UI MVP utilisable sans dépendre implicitement des mocks.

### Scope IN
- Brancher vues clés sur endpoints MVP
- Afficher explicitement fallback « Données simulées »
- États erreur/empty robustes côté UI

### Scope OUT
- Refonte UX complète de l’application
- Nouveau design system

### Prérequis
- EPIC A partiellement livré (contrats API minimum stables)
- Frontend statique servi sur `:5173`

### Fichiers cibles
- `copilot-app/frontend/app/app.js`
- `copilot-app/frontend/app/mockData.js`
- `copilot-app/frontend/app/index.html`
- `copilot-app/frontend/app/style.css`

### Dépendances
- EPIC A (contrat API)
- EPIC C (tests smoke navigateur)

### Risques
- Couplage fort logique UI legacy + contenu mock massif
- Régression de navigation hub (diamond)

### Critères d’acceptation testables
1. Les sections MVP affichent des données API en priorité.
2. Si fallback mock activé, badge visible et non ambigu.
3. Aucune erreur JS bloquante en console sur parcours MVP.
4. Le parcours principal (ouvrir app, charger data, consulter prévisions/news) fonctionne.

### Commandes de test
```bash
./finance-copilot.sh restart
# Vérif manuelle: http://localhost:5173
# Vérif console browser: aucune erreur bloquante
```

### Evidences attendues
- Captures d’écran des sections MVP
- Extraits console (0 erreurs bloquantes)
- Journal des appels réseau (200 sur endpoints MVP)

---

## EPIC C — Industrialiser qualité et exécution multi-agents qwen

### Objectif
Rendre l’exécution des stories reproductible via qwen orchestrator avec preuves systématiques.

### Scope IN
- Templates de dispatch story/tâche
- Quality gate compact backend + frontend
- Convention d’artefacts de preuves

### Scope OUT
- CI/CD cloud complet
- Observabilité SRE avancée

### Prérequis
- `scripts/qwen_orchestrator.py` opérationnel
- Rôles tmux/agent disponibles (planner/dev/tester/qa)

### Fichiers cibles
- `scripts/qwen_orchestrator.py` (si ajustements prompts/guardrails)
- `scripts/analyze_orchestrator_runs.py`
- `finance-app/openclaw-gates/` (artefacts)
- `docs/planning/*.md`

### Dépendances
- EPIC A/B pour valider gates sur vrai périmètre

### Risques
- Dérive de scope des agents
- Preuves incomplètes ou non auditables

### Critères d’acceptation testables
1. Chaque story exécutée produit un bloc: DELTA, EVIDENCE, RISKS, NEXT.
2. Un gate unique donne verdict PASS/BLOCKED pour le MVP.
3. Les artefacts de run sont traçables par run_id horodaté.

### Commandes de test
```bash
python3 scripts/qwen_orchestrator.py --tmux-cmd status
python3 scripts/analyze_orchestrator_runs.py --runs-dir finance-app/orchestrator-runs --limit 5
```

### Evidences attendues
- `finance-app/orchestrator-runs/<run_id>/transcript.md`
- `events.jsonl` + `agent_activity.json`
- Rapport gate dans `finance-app/openclaw-gates/`

---

## Statut d’exécution recommandé (delta)

- **EPIC A**: READY_FOR_EXECUTION (priorité P0)
- **EPIC B**: READY_BLOCKED_BY_A (priorité P1)
- **EPIC C**: IN_PREP (priorité P0.5, en parallèle de A pour le gate)

## Dispatch readiness (delta 19:50)

- **EPIC A**
  - Batch actif: `Batch-01`
  - Tâches ouvertes immédiates: `T-A1.1`, `T-A2.1`
  - Condition de progression: preuves PASS + aucun 500 nominal
- **EPIC B**
  - État: `HOLD_UNTIL_A_CONTRACT_LOCK`
  - Préparation autorisée: revue mapping UI cible sans implémentation
- **EPIC C**
  - État: `PARALLEL_PREP`
  - Action autorisée: préparer gabarit rapport gate sous `finance-app/openclaw-gates/`

## Matrice de gate inter-epics (delta 20:05)
- **Gate G-A (EPIC A -> EPIC B)**
  - Conditions PASS: T-A1.1 + T-A2.1 validées avec preuves
  - Bloqueurs: absence de tests verts ou payload non conforme
  - Décision: `ALLOW_B1` ou `HOLD_B`
- **Gate G-C (EPIC A/B -> EPIC C final)**
  - Conditions PASS: endpoints MVP stables + smoke exploitable
  - Bloqueurs: artefacts incomplets (`DELTA/EVIDENCE/RISKS/NEXT` manquants)
  - Décision: `RUN_FINAL_GATE` ou `BLOCKED_FIX_FIRST`

## Delta orchestration par epic (cycle 20:20)

### EPIC A (P0) — mode EXEC_NOW
- **Lot autorisé**: Batch-01 (`T-A1.1` + `T-A2.1`)
- **Critère de fermeture lot**: verdict QA PASS avec artefact gate auditable
- **Escalade BLOCKED**: si test health échoue ou contrat SPY incomplet

### EPIC B (P1) — mode HOLD_STRICT
- **Règle**: aucune implémentation frontend tant que Gate G-A != `ALLOW_B1`
- **Travail autorisé**: préparation mapping payloads uniquement (sans commit code runtime)

### EPIC C (P0.5) — mode EVIDENCE_ENFORCER
- **Action active**: garantir un template gate unique dans `finance-app/openclaw-gates/`
- **Contrôle**: rejeter tout lot sans bloc `DELTA/EVIDENCE/RISKS/NEXT/VERDICT`

## Delta readiness epics (cycle 20:35)

### EPIC A — état opérationnel renforcé
- **Execution mode**: `RUNNING_ON_APPROVAL`
- **Batch autorisé**: Batch-01 uniquement
- **Condition de fermeture EPIC-A/lot**: artefact gate + PASS QA signé

### EPIC B — garde-fou renforcé
- **Execution mode**: `LOCKED_BY_GATE_G-A`
- **Travail permis**: préparation mapping payloads/documentation
- **Travail interdit**: modifications runtime UI

### EPIC C — rôle de contrôle qualité explicite
- **Execution mode**: `GATE_AUTHORITY`
- **Livrable attendu**: validation formelle du verdict PASS/BLOCKED avant ouverture du lot suivant

## Changelog
- 2026-02-24 19:46 America/New_York — Ajout d’un statut d’exécution incrémental par epic (priorités et dépendances de lancement).
- 2026-02-24 19:50 America/New_York — Ajout readiness de dispatch par epic (Batch-01 actif, B en hold dépendant du lock contrat A, C en préparation parallèle).
- 2026-02-24 20:05 America/New_York — Ajout d’une matrice de gate inter-epics (G-A, G-C) pour clarifier décisions ALLOW/HOLD/BLOCKED pendant le dispatch qwen.
- 2026-02-24 20:20 America/New_York — Passage en orchestration stricte par epic: A en EXEC_NOW, B en HOLD_STRICT dépendant de G-A, C en enforcement de preuves obligatoires.
- 2026-02-24 20:35 America/New_York — Renforcement de readiness: A en RUNNING_ON_APPROVAL, B verrouillé strictement par Gate G-A, C établi comme autorité de verdict avant tout lot suivant.
