# Orchestrator Ops — Findings

## Changelog
- Initialized.

## 2026-02-24 22:55 ET — Scrum friction scan (orchestrator-improvement-loop)

### Signals observés
1. **DoR violation (structure backlog/queue)**
   - `BATCH-01` est en `IN_SPRINT` dans la priority queue alors que le workflow de préflight attend un état valide différent (blocage explicite en WORKSTATE).
   - Impact: dispatch impossible, boucle d’amélioration bloquée avant exécution.

2. **DoD miss (preuve incomplète / verdict non exploitable)**
   - Sprint: `DONE: none`, blockers actifs sur artefacts PASS manquants (`BATCH01_ARTIFACT_MISSING`).
   - Le run analysé génère des sorties longues/bruitées (23 warnings, 24 auto-rewrites), sans passage clair d’une gate DoD compacte exploitable.

3. **Carry-over risk élevé (début de sprint déjà bloqué)**
   - Sprint W09 démarre avec 3 stories P0 en cours + blockers structurels non résolus.
   - Aucun item terminé au snapshot, risque de report inter-sprint élevé.

4. **Blocked recurrence (récurrence de blocants système)**
   - Blocants répétés: `preflight_blocked_by_priority_queue_state_validation`, `ORCH-ENV-PROJECT-DIR` (paths macOS invalides sur VM Linux), dépendance BATCH-02→BATCH-01.

5. **Cycle-time inflation (temps de cycle process, pas CPU)**
   - Le run observé totalise 59 turns / ~426s avec forte verbosité et répétitions, ce qui ralentit la convergence vers un verdict actionnable.

### Métriques factuelles
- Runs analysés: 1
- Turns: 59
- Warnings: 23
- Réponses longues: 8
- Réécritures auto: 24
- DONE sprint: 0
- BLOCKED sprint: 3 (dont 2 structurels, 1 dépendance)