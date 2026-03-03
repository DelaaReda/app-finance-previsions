# WORKSTATE (MVP Planner Continuity)
_Mis à jour: 2026-03-03 par planner/admin (alignement lean BATCH-26)_

## ⚡ LECTURE OBLIGATOIRE À CHAQUE RUN

**1. Lis d'abord:** `docs/product/planning/PRODUCT_VISION.md` — c'est la source de vérité du produit.
**2. Ensuite:** ce fichier pour l'état actuel.
**3. Puis:** `docs/orchestrator-ops/parallel-workstreams.json` pour les tâches en cours.

---

## État Actuel (2026-03-03 16:15 EST)

- **Phase:** architecture_hardening_blocker
- **Batch actif:** BATCH-26 (Architecture Hardening Pack — audit 2026-03-03)
- **Slot planner:** claim `BATCH-26-PLAN` puis dispatch strict `BATCH-26-DEV-01/02/03`
- **Action immédiate:** exécuter la chaîne `PLAN -> DEV-01 -> DEV-02 -> DEV-03 -> ADMIN-01 -> GOV-REVIEW` avec preuves runtime

## Gate Truth

| Batch | État | Artefact |
|-------|------|---------|
| BATCH-01 | ✅ CLOSED/PASS | `finance-app/openclaw-gates/batch-01-20260225-000127.md` |
| BATCH-02 | ✅ CLOSED/PASS | `finance-app/openclaw-gates/batch-02-20260225-202042.md` |
| BATCH-03 | ✅ CLOSED/PASS | priority-queue.json state=CLOSED |
| BATCH-04 | ✅ CLOSED/PASS | `docs/operations/orchestrator/proofs/BATCH-04/BATCH-04-COMPLETION-20260302T002500Z.yaml` |
| BATCH-05 | ✅ CLOSED | priority-queue + workboard: fermé (handoff vers BATCH-06) |
| BATCH-06 | ✅ CLOSED | priority-queue: CLOSED (batch terminé) |
| BATCH-07 | ✅ CLOSED | priority-queue + workboard: fermé |
| BATCH-08 | 📋 WAITING_DEP | bloqué par BATCH-26 (hardening architecture) |
| BATCH-26 | 🟢 READY | priorité P0 — corriger findings F-001..F-012 avant reprise feature UX |

---

## BATCH-26 — Tâches en cours

**Objectif:** hardening architecture P0/P1 avant reprise features UX/delivery

| Rôle | Tâche | Status |
|------|-------|--------|
| planner | `BATCH-26-PLAN` — cadrer/dispatcher la chaîne hardening + garder queue/workboard synchronisés | done |
| dev | `BATCH-26-DEV-01` — corriger charge module/imports cross-layer (F-001/F-002/F-003) | ready |
| dev | `BATCH-26-DEV-02` — unifier data path runtime + purge fake/runtime fantôme (F-004/F-005/F-006/F-008) | waiting_dep |
| dev | `BATCH-26-DEV-03` — retirer bridges fragiles + durcir validator/spec/runtime (F-010/F-011/F-012/F-015/F-020) | waiting_dep |
| admin | `BATCH-26-ADMIN-01` — valider santé runtime/monitor/cron après patchs dev | waiting_dep |
| planner | `BATCH-26-GOV-REVIEW` — conclure PASS/BLOCKED et débloquer BATCH-08 | waiting_dep |

**Success criteria BATCH-26:**
1. Les corrections F-001..F-012 critiques sont appliquées avec preuves techniques courtes (imports/tests/smoke).
2. Les chemins runtime sont unifiés (`apps/api/runtime/**` canonique) sans artefacts fake actifs.
3. Les prompts/guards empêchent `analysis_only` quand du travail actionnable existe.

**Vision Reference:** `docs/product/planning/tasks.md#addendum-audit-2026-03-03-architecture-hardening-pack-p0p1`

---

## BATCH-04 — Résumé (CLOSED)

**Objectif:** Dashboard Vision — Brief quotidien + Secteurs réels

| Rôle | Tâche | Status |
|------|-------|--------|
| planner | Valider vision conformance (2-3 clics, lisible en 30s) | done ✅ |
| backend_engineer | Endpoint /api/brief/daily avec macro signals + secteurs | done ✅ |
| frontend_engineer | Brief en header + secteurs avec flèches (↑↓→) | done ✅ |
| data_analyst | Pipeline macro indicators fraîcheur < 10min | done ✅ |

**Success criteria BATCH-04:**
1. `curl /api/brief/daily` → texte synthèse < 200 mots ✅
2. Dashboard affiche brief en haut sans scroll ✅
3. Secteurs (or, IA, énergie) ont direction visible (↑↓→) ✅

**Proofs:**
- BACKEND: `docs/operations/orchestrator/proofs/BATCH-04/BATCH-04-BACKEND/20260301T115545Z-972.yaml`
- COMPLETION: `docs/operations/orchestrator/proofs/BATCH-04/BATCH-04-COMPLETION-20260302T002500Z.yaml`

---

## Règles Planner (à appliquer chaque run)

### Protocole de run
1. Lire `docs/product/planning/PRODUCT_VISION.md`
2. Lire ce fichier
3. Vérifier l'état du batch actif dans workboard
4. Si batch actif = IN_PROGRESS → monitorer et débloquer
5. Si batch actif = DONE/PASS → ouvrir le batch suivant (PLANNED → OPEN)
6. Si aucun batch OPEN → créer le prochain selon la roadmap vision

### Check anti-desync (obligatoire avant dispatch)
1. Vérifier queue: `jq -r '.items[] | [.id,.state] | @tsv' docs/operations/orchestrator/priority-queue.json`
2. Vérifier workstreams: `jq -r '.streams[] | [.id,.state] | @tsv' docs/operations/orchestrator/parallel-workstreams.json`
3. Si mismatch sur le batch actif, corriger les états avant tout nouveau claim role.

### Comment ouvrir un batch suivant
```
# Quand BATCH-N est DONE:
1. Vérifier les success_criteria du batch dans workboard
2. Créer artefact gate: finance-app/openclaw-gates/batch-0N-YYYYMMDD-HHMMSS.md
3. Dans workboard: mettre BATCH-N state=CLOSED
4. Dans workboard: mettre BATCH-N+1 state=OPEN, planner_slot=assigned
5. Mettre à jour ce fichier (checkpoint)
6. Dispatcher les tâches BATCH-N+1 aux rôles concernés
```

### Comment dispatcher une tâche à un rôle
```
# Écrire dans memory/agents/<role>.md:
- [2026-XX-XX PLANNER] BATCH-N-ROLE assigné: <description de la tâche>
  Success criteria: <liste>
  Fichiers cibles: <liste>
  Commandes de validation: <curl ou test command>
```

### Si le planner est bloqué
- **Cause commune 1:** Workboard sans slot planner → chercher le batch OPEN et vérifier que BATCH-N-PLAN existe
- **Cause commune 2:** Tâche ambiguë → relire `docs/product/planning/PRODUCT_VISION.md` pour clarification
- **Cause commune 3:** Rôle bloqué → écrire dans `docs/ops/ADMIN_TEAM_CHAT.md` avec tag `[BLOCKER]`

### Ne jamais faire
- ❌ Tourner en boucle sur la même analyse sans livrer
- ❌ Replanifier ce qui est déjà DONE
- ❌ Créer des tâches hors scope MVP (voir PRODUCT_VISION.md §Hors scope)
- ❌ Appeler des LLMs coûteux en boucle sans cache

---

## Changelog

- 2026-02-25 20:20 — BATCH-02 clôturé
- 2026-02-28 (admin-claude) — BATCH-03 créé + workboard rempli jusqu'à BATCH-07. PRODUCT_VISION.md créé. Cron path corrigé. apiConnector.js créé.
- 2026-03-01 (admin-claude) — BATCH-03 CLOSED, BATCH-04 ouvert
- 2026-03-02 (planner) — BATCH-04 CLOSED, BATCH-05 ouvert et dispatché
- 2026-03-03 (planner/admin) — BATCH-05 clos, BATCH-06 READY, renommage des sous-tâches actives en lane dev (`DEV-01/02/03`) pour éviter la confusion de labels.
- 2026-03-03 (planner/admin) — Ajout BATCH-26 (P0 architecture hardening) suite audit live; BATCH-08 remis en WAITING_DEP jusqu'à PASS hardening.
- 2026-03-03 (planner/admin) — BATCH-26 aligné en chaîne lean `PLAN -> DEV-01/02/03 -> ADMIN-01 -> GOV-REVIEW` (suppression des labels actifs backend/frontend/data).
