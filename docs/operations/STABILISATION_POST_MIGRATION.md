# Plan de Stabilisation Post-Migration

**Date:** 2026-02-28 06:00 EST  
**Inspecteur:** En charge  
**Status:** ⚠️ EN COURS - URGENT

---

## 📋 CONTEXTE

### **Migration Effectuée (Feb 27-28, 2026)**

- **Structure:** Refactorisation complète vers `apps/api/`, `platform/`, `packages/`
- **Durée:** ~6 heures
- **Status:** ✅ Structure migrée, ⚠️ Stabilisation requise

### **Problèmes Post-Migration**

1. 🔴 **Health endpoint:** `last_updates: {}` (vide)
2. 🔴 **Crons:** 17/17 en erreur (API rate limit)
3. 🔴 **Jobs:** Non réactivés post-migration
4. ⚠️ **RAG fake:** Données test toujours présentes
5. ⚠️ **Sessions tmux:** 10/12 actives mais bloquées

---

## 🎯 OBJECTIF

**Retour à un état stable COMME AVANT migration, TOUT EN conservant la NOUVELLE architecture.**

### **État Stable Cible:**

| Composant | État Avant | État Cible |
|-----------|------------|------------|
| **Health endpoint** | ✅ `last_updates` rempli | ✅ Identique |
| **Crons** | ✅ 17/17 OK | ✅ 17/17 OK |
| **Jobs** | ✅ Tournent | ✅ Tournent |
| **RAG** | ✅ Vraies données | ✅ Vraies données |
| **Sessions tmux** | ✅ 12/12 actives | ✅ 12/12 actives |
| **Agents** | ✅ Codex Pro | ⚠️ Qwen (limites Codex) |
| **Architecture** | ❌ Ancienne | ✅ **NOUVELLE** |

---

## 📊 ÉTAT ACTUEL (2026-02-28 06:00 EST)

### **✅ Ce Qui Fonctionne:**

- ✅ Backend UP (http://localhost:8050)
- ✅ Frontend UP (http://localhost:5173)
- ✅ Nouvelle architecture en place
- ✅ Qwen CLI installé et configuré
- ✅ Sessions tmux (10/12) actives
- ✅ Documentation créée

### **🔴 Ce Qui Est Brisé:**

- 🔴 Health endpoint: `last_updates: {}`
- 🔴 Crons: 17/17 en erreur (API rate limit)
- 🔴 Jobs: Non réactivés
- 🔴 RAG: Fake data présente
- 🔴 Agents: Limites Codex Pro atteintes

---

## 🔧 PLAN DE STABILISATION

### **PHASE 0: URGENCE (0-1h)**

**Objectif:** Arrêter l'hémorragie

#### **0.1: Purge RAG Fake Data**

```bash
# Localiser et purger
find apps/api/runtime -name "news.jsonl" -type f -exec cat {} \;
find apps/api/runtime -name "news.jsonl" -type f -exec rm -v {} \;

# Vérifier purge
find apps/api/runtime -name "news.jsonl" -type f
# Doit retourner: (vide)
```

**Preuve requise:**
```bash
cat apps/api/runtime/data/rag/news.jsonl 2>&1
# Doit retourner: No such file or directory
```

---

#### **0.2: Suspendre Crons Codex**

```bash
# Lister crons en erreur
openclaw cron list | grep error

# Suspendre pour économie tokens
openclaw cron disable ea27cf27-7986-4925-9c16-1d2db1672717  # stale-sweep
openclaw cron disable 742ed606-8aaa-4a66-a521-aaab044eaf54  # admin-agents
# ... (tous les crons en erreur)
```

**Preuve requise:**
```bash
openclaw cron list | grep -E "enabled|disabled" | head -20
```

---

#### **0.3: Vérifier Auth Qwen**

```bash
# Vérifier token
cat ~/.openclaw/agents/planner/agent/models.json | jq '.providers["qwen-portal"]'

# Tester connexion
qwen --help

# Vérifier logs d'erreur
cat ~/.openclaw/cron/logs/*.log | grep -i "auth\|rate limit\|qwen" | tail -20
```

**Preuve requise:**
```bash
qwen --version
# Doit retourner: 0.10.6
```

---

### **PHASE 1: RELOAD JOBS (1-2h)**

**Objectif:** Relancer les jobs avec nouvelle structure

#### **1.1: Identifier Jobs à Relancer**

```bash
# Lister jobs dans nouvelle structure
ls apps/api/src/platform/legacy/jobs/

# Jobs critiques:
# - news_ingest.py
# - forecasts.py
# - judge_enrich.py
# - macro_ingest.py
```

---

#### **1.2: Relancer News Ingest**

```bash
cd apps/api/src

# Activer venv
.venv/bin/activate

# Lancer job
python -m platform.legacy.jobs.news_ingest

# Vérifier sortie
tail -f apps/api/runtime/logs/news_ingest.log
```

**Preuve requise:**
```bash
curl http://localhost:8050/api/news/feed?limit=3 | jq '.data.count'
# Doit retourner: > 0
```

---

#### **1.3: Relancer Forecasts**

```bash
cd apps/api/src

# Lancer job
python -m platform.legacy.jobs.forecasts

# Vérifier sortie
tail -f apps/api/runtime/logs/forecasts.log
```

**Preuve requise:**
```bash
curl http://localhost:8050/api/forecasts?limit=3 | jq '.data.count'
# Doit retourner: > 0
```

---

#### **1.4: Vérifier Health Endpoint**

```bash
# Tester endpoint
curl http://localhost:8050/api/health | jq '.last_updates'

# Doit retourner:
# {
#   "forecasts": "2026-02-28T...",
#   "news": "2026-02-28T...",
#   "brief_weekly": "2026-02-28T..."
# }
```

**Preuve requise:**
```bash
curl http://localhost:8050/api/health | jq '.last_updates' | grep -c "2026"
# Doit retourner: >= 3
```

---

### **PHASE 2: REACTIVER CRONS (2-4h)**

**Objectif:** Réactiver crons avec Qwen

#### **2.1: Vérifier Model Config**

```bash
# Vérifier config actuelle
grep "^AGENT_BIN=" platform/automation/cron_tmux_role_runner.sh
grep "^DEFAULT_CODEX_MODEL=" platform/automation/cron_tmux_role_runner.sh

# Doit retourner:
# AGENT_BIN="${TMUX_ROLE_AGENT_BIN:-qwen}"
# DEFAULT_CODEX_MODEL="${MODEL_CONFIG_PARALLEL_ROLE_MODEL:-qwen/qwen3-235b-a22b}"
```

**Status:** ✅ **Déjà configuré Qwen**

---

#### **2.2: Recréer Crons avec Qwen**

```bash
# Backup crons actuels
openclaw cron list --json > /tmp/crons_backup_$(date +%Y%m%d_%H%M%S).json

# Supprimer anciens crons (en erreur)
for cron_id in $(openclaw cron list --json | jq -r '.[] | select(.state.status == "error") | .id'); do
  openclaw cron delete "$cron_id"
done

# Recréer avec Qwen
bash scripts/configure_parallel_team_crons.sh --apply --enable

# Vérifier status
openclaw cron list | head -20
```

**Preuve requise:**
```bash
openclaw cron list | grep -c "error"
# Doit retourner: 0
```

---

#### **2.3: Tester Exécution Cron**

```bash
# Tester manuel
openclaw cron run <cron_id>

# Vérifier logs
tail -f ~/.openclaw/cron/logs/<cron_id>.log

# Vérifier que Qwen est utilisé
grep -i "qwen" ~/.openclaw/cron/logs/<cron_id>.log | tail -5
```

**Preuve requise:**
```bash
cat ~/.openclaw/cron/logs/<cron_id>.log | grep -c "qwen"
# Doit retourner: > 0
```

---

### **PHASE 3: VALIDATION (4-6h)**

**Objectif:** Valider état stable

#### **3.1: Checklist de Validation**

- [ ] **Health endpoint:** `last_updates` rempli (>= 3 timestamps)
- [ ] **News feed:** > 100 articles
- [ ] **Forecasts:** > 5 prévisions
- [ ] **Crons:** 0/17 en erreur
- [ ] **Sessions tmux:** 12/12 actives
- [ ] **RAG:** Fake data purgée
- [ ] **Logs:** Aucune erreur critique

---

#### **3.2: Tests Endpoints**

```bash
# Health
curl http://localhost:8050/api/health | jq '{
  status: .status,
  last_updates_count: (.last_updates | length),
  backend_up: .backend_up
}'

# News
curl http://localhost:8050/api/news/feed?limit=5 | jq '{
  count: .data.count,
  total: .data.total,
  freshness: .data.freshness
}'

# Forecasts
curl http://localhost:8050/api/forecasts?limit=5 | jq '{
  count: .data.count,
  last_update: .data.last_update
}'

# Copilot (test RAG purge)
curl -X POST http://localhost:8050/api/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Test"}' | jq '{
  model: .data.model,
  sources_count: .data.sources_count,
  has_fake: (.data.answer | contains("Test News Item"))
}'
```

**Preuves requises:**
```json
{
  "status": "ok",
  "last_updates_count": 3,
  "backend_up": true
}
```

---

#### **3.3: Tests Crons**

```bash
# Lister crons
openclaw cron list | grep -E "error|enabled"

# Vérifier logs récents
find ~/.openclaw/cron/logs -name "*.log" -mmin -60 | xargs tail -20

# Vérifier exécutions réussies
cat ~/.openclaw/cron/role-state/*.jsonl | jq 'select(.type == "turn.completed")' | tail -5
```

**Preuves requises:**
```bash
openclaw cron list | grep -c "error"
# Doit retourner: 0
```

---

### **PHASE 4: DOCUMENTATION (6-8h)**

**Objectif:** Documenter état stable

#### **4.1: Mettre à Jour README.md**

```markdown
# Finance Copilot – État Stable (Post-Migration)

## Architecture (Feb 2026)

- Backend: `apps/api/src/`
- Frontend: `apps/web/src/`
- Runtime: `apps/api/runtime/`
- Platform: `platform/`
- Packages: `packages/`

## Démarrage

```bash
./finance-copilot.sh restart
```

## Status

- ✅ Backend UP
- ✅ Frontend UP
- ✅ Crons: 17/17 OK
- ✅ Jobs: Actifs
- ✅ Qwen: Agent par défaut
```

---

#### **4.2: Créer Runbook de Recovery**

```bash
cat > docs/ops/STABLE_STATE_RUNBOOK.md << 'EOF'
# Runbook: Retour à État Stable

## En cas de problème post-migration

### 1. Vérifier Health
curl http://localhost:8050/api/health | jq '.last_updates'

### 2. Recharger Jobs
cd apps/api/src
.venv/bin/python -m platform.legacy.jobs.news_ingest
.venv/bin/python -m platform.legacy.jobs.forecasts

### 3. Vérifier Crons
openclaw cron list | grep error

### 4. Redémarrer Sessions
tmux kill-session -t <session>
bash scripts/cron_tmux_role_runner.sh <role>
EOF
```

---

#### **4.3: Mettre à Jour Monitoring**

```bash
# Créer script de monitoring
cat > scripts/monitor_stable_state.sh << 'EOF'
#!/bin/bash
# Monitoring état stable post-migration

echo "=== Stable State Monitor ==="
echo "Date: $(date)"
echo ""

# Health check
echo "1. Health Endpoint:"
curl -s http://localhost:8050/api/health | jq '.last_updates | length' | xargs -I {} echo "   Last updates: {}"

# Crons check
echo ""
echo "2. Crons Status:"
openclaw cron list 2>/dev/null | grep -c "error" | xargs -I {} echo "   Errors: {}"

# Sessions check
echo ""
echo "3. Tmux Sessions:"
tmux ls 2>/dev/null | wc -l | xargs -I {} echo "   Active: {}"

echo ""
echo "=== End Monitor ==="
EOF

chmod +x scripts/monitor_stable_state.sh
```

---

## 📊 MÉTRIQUES DE SUCCÈS

### **Avant Stabilisation:**

| Métrique | Valeur | Status |
|----------|--------|--------|
| `last_updates` | `{}` (vide) | 🔴 |
| Crons OK | 0/17 | 🔴 |
| Jobs actifs | 0/4 | 🔴 |
| RAG fake | ✅ Présent | 🔴 |
| Sessions tmux | 10/12 | ⚠️ |

### **Après Stabilisation (Cible):**

| Métrique | Valeur | Status |
|----------|--------|--------|
| `last_updates` | >= 3 timestamps | ✅ |
| Crons OK | 17/17 | ✅ |
| Jobs actifs | 4/4 | ✅ |
| RAG fake | ❌ Purge | ✅ |
| Sessions tmux | 12/12 | ✅ |

---

## ⚠️ RISQUES ET MITIGATIONS

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Échec reload jobs | 🟠 Moyenne | Élevé | Backup data avant |
| Crons échouent | 🟠 Moyenne | Moyen | Tester manuel avant |
| Auth Qwen expire | 🟡 Faible | Élevé | Vérifier token |
| Perte données | 🟡 Faible | Critique | Backup runtime/data |
| Architecture instable | 🟡 Faible | Élevé | Rollback plan prêt |

---

## 📋 CHECKLIST FINALE

### **Phase 0 (Urgence):**
- [ ] RAG fake data purgée
- [ ] Crons Codex suspendus
- [ ] Auth Qwen vérifiée

### **Phase 1 (Reload Jobs):**
- [ ] News ingest relancé
- [ ] Forecasts relancés
- [ ] Health endpoint OK

### **Phase 2 (Crons):**
- [ ] Anciens crons supprimés
- [ ] Nouveaux crons créés avec Qwen
- [ ] Tests exécution OK

### **Phase 3 (Validation):**
- [ ] Tous endpoints OK
- [ ] Tous crons OK
- [ ] Toutes sessions OK
- [ ] Aucune erreur critique

### **Phase 4 (Documentation):**
- [ ] README.md mis à jour
- [ ] Runbook créé
- [ ] Monitoring en place

---

**NEXT:** Exécution Phase 0 (Urgence) immédiate.

---

*Document créé par inspecteur - 2026-02-28 06:00 EST*  
**Status:** ⏳ En attente d'exécution
