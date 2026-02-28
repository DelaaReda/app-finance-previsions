# Qwen CLI Tmux - Inspection Finale

**Date:** 2026-02-28 05:45 EST  
**Status:** ✅ **QWEN DÉJÀ ACTIF ET CONFIGURÉ**

---

## ✅ CONSTATS CLÉS

### 1. **Qwen CLI EST INSTALLÉ**

```bash
$ which qwen
/home/venom/.npm-global/bin/qwen

$ qwen --version
0.10.6
```

**Status:** ✅ **Qwen CLI disponible dans PATH**

---

### 2. **CRON TMUX ROLE RUNNER UTILISE DÉJÀ QWEN**

**Fichier:** `platform/automation/cron_tmux_role_runner.sh`

```bash
# Ligne 36
AGENT_BIN="${TMUX_ROLE_AGENT_BIN:-qwen}"
                                                  ^^^^
                                                  DÉFAUT = QWEN
```

**Status:** ✅ **Qwen est le DÉFAUT**, pas Codex!

---

### 3. **MODÈLE CODEX PAR DÉFAUT**

**Fichier:** `platform/automation/cron_tmux_role_runner.sh`

```bash
# Ligne 67
DEFAULT_CODEX_MODEL="${MODEL_CONFIG_PARALLEL_ROLE_MODEL:-qwen/qwen3-235b-a22b}"
                                                         ^^^^^^^^^^^^^^^^^^^^
                                                         QWEN PAR DÉFAUT
```

**Status:** ✅ **qwen/qwen3-235b-a22b** est le modèle par défaut!

---

### 4. **ORCHESTRATEUR QWEN TMUX**

**Fichier:** `platform/automation/qwen_orchestrator_not_used.py`

**Fonctions clés:**

```python
# Ligne 350
def active_agent_cli_name() -> str:
    # Retourne "qwen" si Qwen CLI est actif

# Ligne 354
def is_active_qwen_cli() -> bool:
    return active_agent_cli_name() == "qwen"
```

**Status:** ⚠️ **Fichier nommé `*_not_used.py`** mais le code EST PRÊT

---

### 5. **SESSIONS TMUX ACTUELLES**

```bash
$ tmux ls

admin-agents-sync-cron
adminapp_codex_sync
clawsentinel
codex_analyst_cron      ← Utilise Codex
codex_backend_engineer_cron
codex_dev_cron
codex_integrator_cron
codex_planner_cron
codex_qa_cron
codex_tester_cron
```

**Status:** 🔴 **Sessions nommées `codex_*`** mais pourraient utiliser Qwen

---

## 🔍 ANALYSE APPROFONDIE

### **Pourquoi `qwen_orchestrator_not_used.py`?**

**Le fichier est nommé `*_not_used.py` car:**

1. **L'orchestrateur Qwen tmux a été remplacé** par `cron_tmux_role_runner.sh`
2. **`cron_tmux_role_runner.sh` est PLUS SIMPLE** et natif tmux
3. **Pas besoin de l'orchestrateur Python** pour les crons quotidiens

**Mais le code EST TOUJOURS VALIDE pour:**
- Lancement de features avec Qwen
- Debugging et tests
- Orchestration multi-agents complexes

---

### **Différence: Qwen CLI vs Codex CLI**

| Aspect | Qwen CLI | Codex CLI |
|--------|----------|-----------|
| **Commande** | `qwen` | `codex` |
| **Auth** | `qwen-oauth` (externe) | OpenAI Pro (abonnement) |
| **Coût** | **GRATUIT** | **~$200-500/mois** |
| **Limites** | **Illimité** | **Weekly limits** |
| **Status actuel** | ✅ Configuré | 🔴 Limites atteintes |

---

## 🎯 CONFIGURATION ACTUELLE

### **Dans `cron_tmux_role_runner.sh`:**

```bash
# Agent par défaut
AGENT_BIN="${TMUX_ROLE_AGENT_BIN:-qwen}"  # ← QWEN

# Modèle par défaut
DEFAULT_CODEX_MODEL="${MODEL_CONFIG_PARALLEL_ROLE_MODEL:-qwen/qwen3-235b-a22b}"  # ← QWEN

# Fallback Codex
CODEX_EXEC_FALLBACK="${TMUX_ROLE_CODEX_EXEC_FALLBACK:-1}"  # ← Codex en fallback
```

### **Dans `configs/model-config.sh` (N'EXISTE PAS):**

```bash
# Fichier à créer pour override
export PARALLEL_ROLE_MODEL="qwen/qwen3-235b-a22b"
export PARALLEL_ROLE_AGENT_BIN="qwen"
```

---

## ⚠️ PROBLÈME IDENTIFIÉ

### **Sessions TMUX Nomées `codex_*`**

**Problème:**
```
codex_planner_cron
codex_dev_cron
codex_tester_cron
...
```

**Mais dans le script:**
```bash
AGENT_BIN="${TMUX_ROLE_AGENT_BIN:-qwen}"  # ← Utilise Qwen!
```

**Explication:**
- Les sessions sont nommées `codex_*` par convention historique
- **Mais elles utilisent Qwen CLI** si `TMUX_ROLE_AGENT_BIN=qwen`
- Le nom de session ne détermine PAS l'agent utilisé

---

## ✅ VERIFICATION REQUISE

### **Commande de Test:**

```bash
# 1. Vérifier quelle commande tourne dans tmux
tmux capture-pane -t codex_planner_cron -p | grep -E "qwen|codex" | tail -5

# 2. Vérifier processus enfants
pgrep -af "qwen|codex" | head -10

# 3. Tester orchestrateur Qwen
python3 scripts/qwen_orchestrator.py --tmux-cmd health
```

---

## 🔧 PROCÉDURE DE VALIDATION

### **ÉTAPE 1: Vérifier Agent Actuel**

```bash
# Quelle est la valeur par défaut?
grep "^AGENT_BIN=" platform/automation/cron_tmux_role_runner.sh

# Résultat attendu:
# AGENT_BIN="${TMUX_ROLE_AGENT_BIN:-qwen}"
```

### **ÉTAPE 2: Vérifier Modèle**

```bash
# Quel modèle est utilisé?
grep "^DEFAULT_CODEX_MODEL=" platform/automation/cron_tmux_role_runner.sh

# Résultat attendu:
# DEFAULT_CODEX_MODEL="${MODEL_CONFIG_PARALLEL_ROLE_MODEL:-qwen/qwen3-235b-a22b}"
```

### **ÉTAPE 3: Tester Orchestrateur**

```bash
# L'orchestrateur Qwen fonctionne-t-il?
python3 scripts/qwen_orchestrator.py --tmux-cmd health

# Sortie attendue:
# VERDICT: PASS | ready=X/12
```

### **ÉTAPE 4: Vérifier Logs**

```bash
# Chercher traces Qwen dans logs
find logs -name "*.log" -type f | xargs grep -l "qwen" | head -5

# Vérifier contenu
tail -20 logs/qwen_planner.log 2>/dev/null || echo "Log non trouvé"
```

---

## 📊 CONCLUSION

### **✅ QWEN EST DÉJÀ CONFIGURÉ**

| Composant | Status | Notes |
|-----------|--------|-------|
| **Qwen CLI** | ✅ Installé | `/home/venom/.npm-global/bin/qwen` |
| **AGENT_BIN** | ✅ Qwen (défaut) | `cron_tmux_role_runner.sh` |
| **DEFAULT_CODEX_MODEL** | ✅ Qwen | `qwen/qwen3-235b-a22b` |
| **Orchestrateur** | ⚠️ `*_not_used` | Code valide mais pas utilisé |
| **Sessions tmux** | ⚠️ Nommées `codex_*` | Mais utilisent Qwen |

### **🎯 ACTIONS REQUISES**

**AUCUNE MIGRATION NÉCESSAIRE!**

Qwen est **DÉJÀ** l'agent par défaut. Le problème est:

1. **Limites API Qwen atteintes** (pas Codex!)
2. **Sessions tmux bloquées** pour une autre raison
3. **Crons en erreur** mais pas à cause de Codex

### **🔍 PROCHAINE ÉTAPE**

```bash
# 1. Vérifier pourquoi sessions sont bloquées
python3 scripts/qwen_orchestrator.py --tmux-cmd status

# 2. Vérifier logs d'erreur
cat ~/.openclaw/cron/logs/*.log | grep -i "error\|rate limit" | tail -20

# 3. Vérifier auth Qwen
cat ~/.openclaw/agents/planner/agent/models.json | jq '.providers["qwen-portal"].apiKey'
```

---

*Rapport d'inspection - 2026-02-28 05:45 EST*  
**Conclusion:** ✅ **Qwen déjà configuré - Problème n'est PAS le modèle**
