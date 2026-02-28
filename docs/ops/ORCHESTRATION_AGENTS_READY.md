# Orchestration – Prêt pour agents (2026-02-28)

**Objectif:** Checklist de validation et correction des blocages les plus fréquents avant réactivation des agents.

---

## ✅ Validations préalables (à exécuter avant réactivation)

```bash
# 1. Plomberie
bash platform/policies/validate_parallel_plumbing.sh

# 2. Tooling
bash platform/automation/dev_qa_tooling_check.sh

# 3. Backend (doit tourner pour les rôles delivery)
curl -s http://localhost:8050/api/health | jq '.status'
bash scripts/backend_regression_gate.sh --no-live

# 4. Preflight
bash scripts/preflight_dispatch.sh

# 5. Workboard / queue
python3 scripts/parallel_workstream.py status
python3 scripts/parallel_workstream.py sync-priority --include-pass
```

---

## Erreurs bloquantes identifiées (logs 2026-02-28)

### 1. ROLE_MENTOR_EVIDENCE_MISSING / ROLE_CONTRACT_MISSING
**Cause:** La sortie du rôle ne contient pas le contrat 8-lignes attendu ou les clés EVIDENCE exigées par le guard.

**Consignes pour les agents:**
- Produire **exactement** les 8 lignes: STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE
- EVIDENCE doit inclure: `run_note=<phrase>=5 mots`, `exec_report=...`, `channels_read=...`, `impact_assessment=...`, `impact_action=...` (si impact medium+)
- Inclure l’artefact rôle: ex. `PLANNER_ARTIFACT=docs/...`, `BACKEND_ARTIFACT=apps/api/src/...`

**Référence:** `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`

**Template minimal (8 lignes obligatoires):**
```
STATUS=IN_PROGRESS
DELTA=NO_DELTA
EVIDENCE=task_update=analysis_only;run_note=...;exec_report=...;channels_read=...;impact_assessment=low;impact_action=...
RISKS=none
NEXT=...
VERDICT=GO_WITH_CAUTION
BLOCKER_ID=NONE
NEXT_ACTION_UNIQUE=...
```

---

### 2. signal_unparseable
**Cause:** Capture tmux ou sortie agent non parsable (format incorrect, caractères bizarres).

**Consignes:**
- Sortie en texte brut, une clé par ligne
- Pas de markdown autour du bloc contrat
- Éviter les caractères `;` dans les valeurs (utiliser `,` ou `_`)

---

### 3. 12 rôles en erreur (admin-agents tick)
**Symptôme:** `unhealthy: planner-tmux-loop, clawsentinel-tmux-loop, backend-engineer-tmux-loop, ...`

**Causes probables:**
- Sessions tmux périmées ou crashées
- Contrat guard qui bloque systématiquement (voir 1 et 2)

**Actions:**
```bash
# Vérifier sessions
tmux list-sessions

# Forcer un re-run des rôles bloqués (admin)
# Voir docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md
```

---

### 4. Chemins obsolètes dans exemples
~~**Problème:** `backend_artifact=copilot-app/backend/src/api/main.py` est encore référencé.~~ → Corrigé (ROLE_CONTRACT_EVIDENCE_SCHEMA, ORCHESTRATION_COORDINATION_SPEC, ENGINEERING_PLAYBOOK)

**Canonique:** `apps/api/src/platform/main.py`, `apps/api/src/domains/judge/api/judge.py`

---

## Specs et chemins canoniques

| Document | Chemin |
|----------|--------|
| ORCHESTRATION_COORDINATION_SPEC | `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml` |
| ROLE_CONTRACT_EVIDENCE_SCHEMA | `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md` |
| PARALLEL_PLUMBING_QUICKSTART | `docs/ops/PARALLEL_PLUMBING_QUICKSTART.md` |
| priority-queue | `docs/orchestrator-ops/priority-queue.json` |
| parallel-workstreams-plumbing | `docs/orchestrator-ops/parallel-workstreams-plumbing.json` |

---

## Ordre de réactivation recommandé

1. **Backend + health** – s’assurer que `./finance-copilot.sh status` montre Backend OK
2. **Plomberie** – `validate_parallel_plumbing.sh` = 18/18
3. **Un rôle pilote** (ex. planner) – vérifier qu’il passe le contract guard
4. **Autres rôles** – activer progressivement

## Supervision continue (copier-coller rapide)

```bash
# 1) Vérifier l'état des sessions tmux
tmux list-sessions -F '#S' | sort

# 2) Vérifier la santé du pipeline d'orchestration
python3 scripts/parallel_workstream.py status

# 3) Vérifier l'état des files (queue + board)
jq '.items[] | {id,state,next_action,owner_role,dispatch_authorized}' docs/orchestrator-ops/priority-queue.json
jq '.streams[] | {id,state,planner_slot}' docs/orchestrator-ops/parallel-workstreams.json

# 4) Relancer un rôle (quand bloqué) via runner
for r in planner frontend_engineer backend_engineer data_analyst; do
  ./scripts/cron_tmux_role_runner.sh \"$r\"
done

# 5) Vérifier activité récente par rôle
for r in planner frontend_engineer backend_engineer data_analyst; do
  echo \"== $r ==\"
  tail -n 12 \"logs-codex-runs/role-runner/${r}.live.log\"
done

# 6) Détection de dérives récurrentes
rg -n \"NO_DELTA|NO_READY|BLOCKED|checkpoint_fallback\" logs-codex-runs/role-runner/*.live.log
```

---

*Voir aussi: `docs/ops/AGENTS_READY.md`, `docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md`*
