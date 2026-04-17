# Qwen Tmux Orchestrator - Guide d'Activation

Historical note:
- This document reflects an older migration/recovery phase.
- Any `localhost:*` app example below is historical only, not current public app guidance.

**Date:** 2026-02-28 05:30 EST  
**Objectif:** Comprendre et activer l'équipe Qwen pour remplacer Codex Pro

---

## 📚 CONSTATS DE L'INSPECTION

### ✅ **Qwen DÉJÀ CONFIGURÉ**

**Fichiers trouvés:**

1. **`~/.openclaw/agents/planner/agent/models.json`** ✅
   - Provider `qwen-portal` configuré
   - Base URL: `https://portal.qwen.ai/v1`
   - API: `openai-completions`
   - Models: `coder-model`, `vision-model`
   - Auth: `qwen-oauth` (token externe)

2. **`platform/config/llm-models.json`** ✅
   ```json
   {
     "g4f": {
       "provider": "DeepInfra",
       "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
     },
     "llm_dev_models": [
       "qwen-3-235b",
       "qwen/qwen3-235b-a22b",
       "deepseek-v3"
     ]
   }
   ```

3. **`scripts/qwen_orchestrator.py`** ✅
   - Symlink vers `platform/automation/qwen_orchestrator_not_used.py`
   - **Status:** ⚠️ **NOT USED** (désactivé)

---

### ⚠️ **ORCHESTRATEUR QWEN DÉSACTIVÉ**

**Problème identifié:**

```bash
# Symlink actuel
scripts/qwen_orchestrator.py -> platform/automation/qwen_orchestrator_not_used.py
```

**Le fichier source est nommé `*_not_used.py`** → Indique que l'orchestrateur Qwen tmux est **désactivé**.

---

### 📊 **ARCHITECTURE QWEN TMUX**

**Sessions tmux attendues:**
```
qwen_planner_cron
qwen_dev_cron
qwen_tester_cron
qwen_qa_cron
qwen_architect_cron
qwen_analyst_cron
qwen_backend_engineer_cron
qwen_frontend_engineer_cron
...
```

**Commande de vérification:**
```bash
python3 scripts/qwen_orchestrator.py --tmux-cmd health --status-format compact
```

**Sortie attendue:**
```
VERDICT: PASS | ready=X/12
```

---

## 🔧 COMPRENDRE L'ORCHESTRATEUR

### **Fonctionnement de `qwen_orchestrator.py`**

**Commandes principales:**

```bash
# 1. Vérifier santé des sessions
python3 scripts/qwen_orchestrator.py --tmux-cmd health

# 2. Vérifier status détaillé
python3 scripts/qwen_orchestrator.py --tmux-cmd status

# 3. Redémarrer sessions
python3 scripts/qwen_orchestrator.py --restart

# 4. Lancer feature avec Qwen
python3 scripts/qwen_orchestrator.py \
  --feature "Ma feature" \
  --agent-bin qwen \
  --prompt-engine tmux
```

**Options clés:**
- `--agent-bin qwen` → Utiliser binaire Qwen au lieu de Codex
- `--qwen-bin /path/to/qwen` → Chemin personnalisé
- `--tmux-cmd health|status` → Vérifier sessions
- `--restart` → Redémarrer sessions tmux
- `--prompt-engine tmux` → Utiliser backend tmux (pas SDK)

---

### **Rôles Supportés**

**Core roles:**
- `planner`
- `dev`
- `tester`
- `qa`

**Specialist roles:**
- `analyst`
- `architect`
- `backend_engineer`
- `frontend_engineer`
- `data_analyst`
- `infra_engineer`
- `integrator`

**Governance roles:**
- `po` (Product Owner)
- `scrum_master`
- `clawsentinel` (Safety/Quality)

---

## 🚨 PROBLÈME ACTUEL

### **Pourquoi Qwen n'est PAS utilisé?**

1. **⚠️ Symlink vers `*_not_used.py`**
   ```bash
   scripts/qwen_orchestrator.py -> platform/automation/qwen_orchestrator_not_used.py
   ```

2. **⚠️ Crons configurés avec Codex**
   ```bash
   ROLE_CODEX_MODEL="gpt-5.3-codex-spark"  # Pas qwen-coder
   ```

3. **⚠️ Sessions tmux actuelles = Codex**
   ```
   codex_planner_cron
   codex_dev_cron
   codex_tester_cron
   ...
   ```

4. **⚠️ Model config non appliquée**
   - `configs/model-config.sh` n'existe pas
   - Variables d'environnement non définies

---

## ✅ PROCÉDURE D'ACTIVATION QWEN

### **ÉTAPE 1: Vérifier Auth Qwen**

```bash
# Vérifier token Qwen
cat ~/.openclaw/agents/planner/agent/models.json | jq '.providers["qwen-portal"].apiKey'

# Doit retourner: "qwen-oauth"
# Vérifier que token est valide
curl -X POST https://portal.qwen.ai/v1/chat/completions \
  -H "Authorization: Bearer $(cat ~/.qwen-token)" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-coder","messages":[{"role":"user","content":"test"}]}'
```

---

### **ÉTAPE 2: Créer model-config.sh**

```bash
# Créer fichier de config
cat > configs/model-config.sh << 'EOF'
#!/bin/bash
# Model Configuration - Qwen Team

# Default model for parallel roles
export PARALLEL_ROLE_MODEL="qwen-coder"

# Thinking level (xhigh, high, medium, low)
export PARALLEL_ROLE_THINKING="high"

# Timeout seconds
export PARALLEL_CRON_TIMEOUT_SECONDS="900"

# Agent binary
export PARALLEL_ROLE_AGENT_BIN="qwen"

# Retry engine
export PARALLEL_ROLE_RETRY_ENGINE_DEFAULT="sdk"

# Qwen specific
export QWEN_BASE_URL="https://portal.qwen.ai/v1"
export QWEN_API_KEY="qwen-oauth"
export QWEN_MODEL="qwen-coder"
EOF

chmod +x configs/model-config.sh
```

---

### **ÉTAPE 3: Activer Orchestrateur Qwen**

**Option A: Utiliser orchestrateur existant**

```bash
# 1. Vérifier si qwen_orchestrator.py fonctionne
python3 scripts/qwen_orchestrator.py --tmux-cmd health

# 2. Si erreur, créer vrai script (pas symlink vers not_used)
cp platform/automation/qwen_orchestrator_not_used.py \
   platform/automation/qwen_orchestrator.py

# 3. Mettre à jour symlink
ln -sfn platform/automation/qwen_orchestrator.py scripts/qwen_orchestrator.py

# 4. Tester
python3 scripts/qwen_orchestrator.py --tmux-cmd health
```

**Option B: Utiliser OpenClaw directement (RECOMMANDÉ)**

```bash
# OpenClaw gère déjà les agents Qwen via models.json
# Juste besoin de changer le modèle dans les crons

# 1. Modifier model-config.sh (voir ÉTAPE 2)

# 2. Mettre à jour crons existants
openclaw cron list --json | jq -r '.[].id' | while read cron_id; do
  # Note: OpenClaw ne permet pas de changer modèle directement
  # Faut recréer les crons
  echo "Cron $cron_id needs recreation with qwen-coder model"
done

# 3. Recréer crons avec Qwen
bash scripts/configure_parallel_team_crons.sh --apply --enable
```

---

### **ÉTAPE 4: Recréer Sessions Tmux Qwen**

```bash
# 1. Tuer sessions Codex actuelles
tmux kill-session -t codex_planner_cron 2>/dev/null || true
tmux kill-session -t codex_dev_cron 2>/dev/null || true
tmux kill-session -t codex_tester_cron 2>/dev/null || true
tmux kill-session -t codex_qa_cron 2>/dev/null || true
# ... (tous les rôles)

# 2. Créer sessions Qwen
TMUX_ROLE_AGENT_BIN=qwen bash scripts/cron_tmux_role_runner.sh planner &
TMUX_ROLE_AGENT_BIN=qwen bash scripts/cron_tmux_role_runner.sh dev &
TMUX_ROLE_AGENT_BIN=qwen bash scripts/cron_tmux_role_runner.sh tester &
TMUX_ROLE_AGENT_BIN=qwen bash scripts/cron_tmux_role_runner.sh qa &
# ... (tous les rôles)

# 3. Vérifier sessions
tmux ls | grep qwen
```

---

### **ÉTAPE 5: Tester Exécution**

```bash
# 1. Vérifier santé
python3 scripts/qwen_orchestrator.py --tmux-cmd health

# Sortie attendue:
# VERDICT: PASS | ready=12/12

# 2. Tester un run manuel
python3 scripts/qwen_orchestrator.py \
  --feature "Test Qwen activation" \
  --agent-bin qwen \
  --rounds 1 \
  --mode debug

# 3. Vérifier logs
tail -f logs/qwen_planner.log
```

---

## 📊 VALIDATION CHECKLIST

- [ ] **Auth Qwen** vérifiée et valide
- [ ] **model-config.sh** créé et configuré
- [ ] **Orchestrateur** activé (pas `*_not_used`)
- [ ] **Sessions tmux** Qwen créées
- [ ] **Health check** PASS (ready=12/12)
- [ ] **Test run** effectué avec succès
- [ ] **Logs** confirment utilisation Qwen
- [ ] **Crons** recréés avec modèle qwen-coder

---

## ⚠️ RISQUES ET MITIGATIONS

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Token Qwen expiré | 🟡 Faible | Élevé | Vérifier validité avant migration |
| Sessions tmux échouent | 🟠 Moyenne | Moyen | Tester manuellement avant bulk |
| Qwen moins performant | 🟡 Faible | Moyen | Surveillance 24h post-migration |
| Orchestrateur bug | 🟡 Faible | Élevé | Garder backup Codex activé |

---

## 🎯 COMMANDES DE VALIDATION

```bash
# 1. Vérifier modèle utilisé par agent
cat ~/.openclaw/agents/planner/agent/models.json | jq '.defaultModel'

# 2. Vérifier sessions tmux
tmux ls | grep -E "qwen|codex"

# 3. Vérifier santé orchestrator
python3 scripts/qwen_orchestrator.py --tmux-cmd health --status-format compact

# 4. Vérifier logs Qwen
find logs -name "*qwen*" -type f | xargs tail -20

# 5. Tester health endpoint
curl http://localhost:8050/api/health | jq '.last_updates'
```

---

## 📋 NEXT

1. ⏳ **Vérifier token Qwen** (auth valide?)
2. ⏳ **Créer model-config.sh**
3. ⏳ **Activer orchestrateur** (copier `qwen_orchestrator.py`)
4. ⏳ **Recréer sessions tmux** avec `TMUX_ROLE_AGENT_BIN=qwen`
5. ⏳ **Tester health check**
6. ⏳ **Recréer crons** avec modèle Qwen

---

*Guide créé par inspecteur - 2026-02-28 05:30 EST*  
**Status:** ⏳ En attente de validation pour exécution
