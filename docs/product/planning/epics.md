# Epics MVP — orientées exécution agents codex (OpenClaw)

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
- `apps/api/src/domains/judge/api/main.py`
- `apps/api/src/domains/judge/api/routes/forecasts.py`
- `apps/api/tests/test_health.py`
- `apps/api/tests/` (nouveaux tests endpoint)

### Dépendances
- Aucune dépendance bloquante (EPIC socle)

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
cd copilot-app/backend && ([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && .venv/bin/pytest -q
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
- `apps/web/src/domains/home/pages/app.js`
- `apps/web/src/domains/home/pages/mockData.js`
- `apps/web/src/domains/home/pages/index.html`
- `apps/web/src/domains/home/pages/style.css`

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

## EPIC C — Industrialiser qualité et exécution (codex/OpenClaw)

### Objectif
Rendre l’exécution des stories reproductible via OpenClaw (codex-only) avec preuves systématiques.

### Scope IN
- Templates de dispatch story/tâche
- Quality gate compact backend + frontend
- Convention d’artefacts de preuves

### Scope OUT
- CI/CD cloud complet
- Observabilité SRE avancée

### Prérequis
- `openclaw` opérationnel côté runtime
- Rôles tmux/agent disponibles (au minimum: planner/dev/tester/qa)
- Spec + preuves alignées (`docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`)

### Fichiers cibles
- `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
- `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`
- `scripts/validate_roles_sequential.sh`
- `scripts/run_delivery_gate.sh`
- `finance-app/openclaw-gates/` (artefacts)
- `docs/planning/*.md`

### Dépendances
- EPIC A/B pour valider gates sur vrai périmètre

### Risques
- Dérive de scope des agents
- Preuves incomplètes ou non auditables

### Critères d’acceptation testables
1. Chaque rôle exécuté produit un contrat complet (8 clés) avec `EVIDENCE` exploitable.
2. Un gate unique donne verdict PASS/BLOCKED pour le MVP.
3. Les artefacts sont traçables par batch/horodatage et vérifiables par script.

### Commandes de test
```bash
bash scripts/preflight_dispatch.sh
SEQUENTIAL_VALIDATE_TIMEOUT_SECONDS=480000 bash scripts/validate_roles_sequential.sh --roles planner,dev,tester,qa --strict-ready-chain --chain-target BATCH-XX
bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/batch-XX-<timestamp>.md
```

### Evidences attendues
- Rapport gate dans `finance-app/openclaw-gates/`
- Rapport `validate_roles_sequential` dans `logs-codex-runs/role-runner/`

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

## Delta coordination inter-epics (cycle 20:50)

### EPIC A
- **Execution intent**: `LAUNCH_NOW`
- **Exit artifact required**: `finance-app/openclaw-gates/batch-01-<timestamp>.md`
- **Verdict authority**: QA (EPIC C)

### EPIC B
- **Execution intent**: `PREP_ONLY`
- **Déclencheur unique**: Gate G-A = `ALLOW_B1`
- **Blocage maintenu**: aucun code runtime UI tant que G-A n’est pas PASS.

### EPIC C
- **Execution intent**: `VERIFY_AND_SIGN`
- **Responsabilité**: contrôler complétude DELTA/EVIDENCE/RISKS/NEXT + VERDICT.
- **Escalade**: tout artefact incomplet = `BLOCKED` automatique.

## Delta orchestration inter-epics (cycle 21:05)

### Décision de phase
- **EPIC A**: `EXECUTION_GATED` (Batch-01 doit produire verdict signé)
- **EPIC B**: `HARD_HOLD` (reste bloqué tant que G-A != ALLOW_B1)
- **EPIC C**: `GATE_ENFORCEMENT_ACTIVE` (autorité de validation du format et verdict)

### Règle de passage renforcée
- Passage A -> B uniquement si artefact Batch-01 contient simultanément:
  - sections `DELTA/EVIDENCE/RISKS/NEXT`
  - ligne `VERDICT: PASS`
  - signature/relecture QA explicite

## Changelog
- 2026-02-24 19:46 America/New_York — Ajout d’un statut d’exécution incrémental par epic (priorités et dépendances de lancement).
- 2026-02-24 19:50 America/New_York — Ajout readiness de dispatch par epic (Batch-01 actif, B en hold dépendant du lock contrat A, C en préparation parallèle).
- 2026-02-24 20:05 America/New_York — Ajout d’une matrice de gate inter-epics (G-A, G-C) pour clarifier décisions ALLOW/HOLD/BLOCKED pendant le dispatch.
- 2026-02-24 20:20 America/New_York — Passage en orchestration stricte par epic: A en EXEC_NOW, B en HOLD_STRICT dépendant de G-A, C en enforcement de preuves obligatoires.
- 2026-02-24 20:35 America/New_York — Renforcement de readiness: A en RUNNING_ON_APPROVAL, B verrouillé strictement par Gate G-A, C établi comme autorité de verdict avant tout lot suivant.
- 2026-02-24 20:50 America/New_York — Ajout d’une coordination inter-epics de lancement: A en LAUNCH_NOW, B en PREP_ONLY conditionné à G-A, C en autorité VERIFY_AND_SIGN avec blocage automatique des artefacts incomplets.
- 2026-02-24 21:05 America/New_York — Renforcement inter-epics: A en `EXECUTION_GATED`, B en `HARD_HOLD`, C en `GATE_ENFORCEMENT_ACTIVE`; passage A->B conditionné à artefact complet + VERDICT PASS + validation QA explicite.
- 2026-02-24 22:05 America/New_York — Correction cohérence de dépendances: EPIC A rendu indépendant (socle), suppression cycle implicite A<->C; commande pytest rendue auto-bootstrap.
- 2026-02-26 America/New_York — Added vision-clarifier epic set focused on personal low-cost decision workflow (`docs/planning/PRODUCT_VISION.md`).
- 2026-02-26 America/New_York — Extended vision epic set with Epic 7/8/9 (macro radar, cost governance, decision learning loop).
- 2026-02-26 America/New_York — Extended vision epic set with Epic 10/11/12/13/14 for basic-ready delivery loop.
- 2026-02-26 America/New_York — Added Epic 15 for explicit data-driven forecasting core (dataset -> training -> backtest -> inference).
- 2026-02-26 America/New_York — Added Epic 16 for strict API->UI forecast delivery contract and release-gate enforcement.

## Delta vision-clarifier (2026-02-26)

This section is the active product-priority lens for upcoming sprints.

### Forecast-first guardrail (global, mandatory)
- Release is invalid if forecast APIs are not data/model-driven on core flows.
- Every decision-facing API must expose forecast provenance and freshness (`source`, `updated_at`, confidence context, fallback visibility).
- UI must render forecast output clearly on decision cards/brief (no hidden fallback, no generic-only answers).
- Gate rule: any flow returning only heuristic/non-data forecast without explicit degraded state => `BLOCKED`.

### Epic 1 (P0) - Data Freshness and Signal Reliability Foundation
- Goal: keep market/context tiles fresh enough for daily decision making.
- Done when:
  - key data surfaces refreshed <= 10 minutes for >= 90% of cycles
  - cache strategy prevents UI stalls and backend overload
  - fallback paths are explicit and auditable

### Epic 2 (P0) - Forecast Engine (Asset/Sector)
- Goal: generate consistent `direction + confidence + action` per target asset/sector.
- Done when:
  - decision contract exists and is stable for MVP universe
  - short (1-3d) and swing (1-2w) horizons are both available
  - no silent schema drift between backend and frontend
  - forecast provenance (`source/model_version/updated_at`) is present or explicit degraded fallback

### Epic 3 (P0) - Multi-Model Consensus and Judge
- Goal: aggregate multiple low-cost model opinions into one final decision signal.
- Done when:
  - at least 3 model/provider opinions are merged per decision cycle
  - judge output is deterministic in shape and includes confidence/risk notes
  - disagreement handling is explicit (conflict mode + reduced confidence)

### Epic 4 (P1) - Decision Cockpit Frontend (2-3 Click Workflow)
- Goal: allow user to open app and get "what to do today" quickly.
- Done when:
  - user can reach daily brief in <= 3 interactions
  - card UI shows action, confidence, rationale, freshness
  - degraded data state is visible (no hidden mock-like behavior)
  - forecast provenance is visible on core decision cards

### Epic 5 (P1) - Ask Copilot Deep Analysis
- Goal: answer tactical questions with grounded market context.
- Done when:
  - question flow returns concise action-oriented answer + evidence
  - answer includes market regime context + risk caveat
  - latency remains practical for daily use
  - answers reference current forecast payloads (not generic-only synthesis)

### Epic 6 (P2) - Portfolio Adaptation Layer
- Goal: align recommendations to user portfolio focus and risk posture.
- Done when:
  - watchlist-centric prioritization exists
  - user can tune aggressiveness (conservative/neutral/aggressive)
  - portfolio action summary is generated daily

### Epic 7 (P2) - Geopolitical and Macro Impact Radar
- Goal: surface macro/geopolitical shocks fast enough to influence same-day decisions.
- Done when:
  - top geopolitical/macro events are ingested with severity and freshness metadata
  - each event maps to impacted assets/sectors in the MVP universe
  - decision brief shows explicit macro risk caveats when regime shifts occur

### Epic 8 (P1) - Cost Governance and Runtime Efficiency
- Goal: keep daily decision workflow low-cost and resilient despite provider instability.
- Done when:
  - free/low-cost providers are primary route by policy
  - cost and fallback metrics are measured per critical AI endpoint
  - delivery gate blocks releases when cost/runtime guardrails are violated

### Epic 9 (P2) - Decision Journal and Learning Loop
- Goal: improve recommendation quality over time from recorded decisions and outcomes.
- Done when:
  - every daily brief decision can be logged with rationale/confidence/sources
  - short-horizon outcomes (1d/1w) are attached to decisions
  - recommendation output includes explicit feedback-weight adjustments

### Epic 10 (P1) - Data Source Reliability and Ingestion Automation
- Goal: ensure core feeds stay available, fresh, and normalized without manual babysitting.
- Done when:
  - source inventory and SLA tiers are defined for core endpoints
  - scheduler + fallback adapters keep core feeds available under source instability
  - ingestion health is exposed to UI and delivery gate

### Epic 11 (P1) - UX Workflow and Personal Settings Basics
- Goal: make daily usage faster and clearer for a solo investor workflow.
- Done when:
  - home information architecture supports 2-3 click decision workflow
  - quick filters and explanation drawer improve action clarity
  - key user preferences persist reliably across sessions

### Epic 12 (P1) - Alerts and Daily Automation
- Goal: surface only actionable events in time, without notification noise.
- Done when:
  - alert rules and triggers run on price/news/regime events
  - in-app alert center and daily digest are available
  - dedupe and prioritization reduce low-value alert spam

### Epic 13 (P1) - Reliability, Security, and Backup
- Goal: make the app recoverable and trustworthy under failures.
- Done when:
  - error catalog + retry policy are enforced on critical flows
  - traceability and backup/restore exist for critical user state
  - recovery drills pass with explicit runbook steps

### Epic 14 (P1) - MVP Release Readiness and Go-Live
- Goal: reach a formal go/no-go decision with auditable proof.
- Done when:
  - checklist and E2E scenarios cover all basic user flows
  - performance and defect thresholds are within release budget
  - final gate returns explicit GO/NO-GO with blocker traceability

### Epic 15 (P0) - Data-Driven Forecasting Core
- Goal: generate forecasts from measurable data pipelines, not only heuristic synthesis.
- Done when:
  - training dataset and feature contract are versioned and reproducible
  - walk-forward backtests validate minimum robustness on MVP horizons
  - runtime forecasts expose explicit model provenance and calibrated confidence
  - nominal runtime path is backed by a real model artifact/version (not snapshot-only heuristic)
  - core UI surfaces display these forecasts and provenance without hidden fallback

### Epic 16 (P0) - Forecast Delivery Contract (API -> UI)
- Goal: guarantee that every core user flow displays live data-driven forecasts from API payloads.
- Done when:
  - forecast contract is unified across `/api/forecasts`, `/api/decision/brief`, `/api/judge`, `/api/copilot/ask`
  - decision UI surfaces (cards/brief/judge/ask) render forecast fields + provenance with no hidden fallback
  - placeholder/mock payloads are removed from core decision flows in nominal mode
  - quality status surfaced in UI is derived from live probes, not static fixtures
  - end-to-end tests prove API payload -> UI rendering on core flows
  - release gate blocks if one core flow misses forecast payload or provenance visibility
