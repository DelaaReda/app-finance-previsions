# WORKSTATE (MVP Planner Continuity)
_Mis à jour: 2026-02-28 par admin-claude après intervention système_

## ⚡ LECTURE OBLIGATOIRE À CHAQUE RUN

**1. Lis d'abord:** `docs/product/planning/PRODUCT_VISION.md` — c'est la source de vérité du produit.
**2. Ensuite:** ce fichier pour l'état actuel.
**3. Puis:** `docs/orchestrator-ops/parallel-workstreams.json` pour les tâches en cours.

---

## État Actuel (2026-02-28)

- **Phase:** batch03_in_progress
- **Batch actif:** BATCH-03 (voir workboard)
- **Slot planner:** ASSIGNÉ dans BATCH-03 (task BATCH-03-PLAN = in_progress)
- **Action immédiate:** Dispatcher BATCH-03 aux rôles et monitorer la livraison

## Gate Truth

| Batch | État | Artefact |
|-------|------|---------|
| BATCH-01 | ✅ CLOSED/PASS | `finance-app/openclaw-gates/batch-01-20260225-000127.md` |
| BATCH-02 | ✅ CLOSED/PASS | `finance-app/openclaw-gates/batch-02-20260225-202042.md` |
| BATCH-03 | 🔄 IN_PROGRESS | workboard: state=OPEN |
| BATCH-04 | 📋 PLANNED | workboard: state=PLANNED |
| BATCH-05 | 📋 PLANNED | workboard: state=PLANNED |
| BATCH-06 | 📋 PLANNED | workboard: state=PLANNED |
| BATCH-07 | 📋 PLANNED | workboard: state=PLANNED |

---

## Règles Planner (à appliquer chaque run)

### Protocole de run
1. Lire `docs/product/planning/PRODUCT_VISION.md`
2. Lire ce fichier
3. Vérifier l'état du batch actif dans workboard
4. Si batch actif = IN_PROGRESS → monitorer et débloquer
5. Si batch actif = DONE/PASS → ouvrir le batch suivant (PLANNED → OPEN)
6. Si aucun batch OPEN → créer le prochain selon la roadmap vision

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

## BATCH-03 — Tâches en cours

**Objectif:** Connecter le frontend aux données réelles + corriger qualité données

**Note admin:** `apiConnector.js` déjà créé dans `apps/web/src/domains/forecasts/contracts/apiConnector.js`

| Rôle | Tâche | Status |
|------|-------|--------|
| planner | Dispatcher + monitorer | in_progress |
| frontend_engineer | Étendre apiConnector.js à tous les widgets | ready |
| backend_engineer | Corriger confidence forecasts (0/19 high), stocks change=0 | ready |
| data_analyst | Activer backtests (actuellement null/pending) | ready |

**Success criteria BATCH-03:**
1. News widget affiche des vraies news (pas mock)
2. Forecasts widget affiche 19 forecasts avec confidence > 0 pour certains
3. Stocks top movers affiche les vrais prix avec % change
4. Backtests: hit_rate > 0 (pas 0.0)

---

## Changelog

- 2026-02-25 20:20 — BATCH-02 clôturé
- 2026-02-28 (admin-claude) — BATCH-03 créé + workboard rempli jusqu'à BATCH-07. PRODUCT_VISION.md créé. Cron path corrigé. apiConnector.js créé.
