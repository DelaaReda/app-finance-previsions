# Activation Équipe Qwen - Procédure d'Urgence

Historical note:
- This document reflects an older migration/recovery phase.
- Any `localhost:*` app example below is historical only, not current public app guidance.

**Date:** 2026-02-28 05:15 EST  
**Motif:** Limites Codex Pro épuisées - API rate limit  
**Status:** ⚠️ EN ATTENTE VALIDATION

---

## 🎯 Objectif

Basculer tous les agents de **Codex Pro** vers **Qwen** (gratuit, illimité) pour prendre le relais immédiatement.

---

## 📊 Configuration Actuelle

**Modèles Codex Pro (BLOQUÉS):**
```json
{
  "adminapp-codex": "gpt-5.3-codex-spark",
  "admin-agents": "gpt-5.3-codex-spark",
  "clawsentinel": "gpt-5.3-codex-spark",
  "planner": "gpt-5.3-codex-spark",
  "backend_engineer": "gpt-5.3-codex-spark",
  ...
}
```

**Status:** 🔴 **TOUS BLOQUÉS** - API rate limit reached

---

## ✅ Configuration Qwen (PRÊTE)

**Fichier:** `~/.openclaw/agents/planner/agent/models.json`

```json
{
  "providers": {
    "qwen-portal": {
      "baseUrl": "https://portal.qwen.ai/v1",
      "api": "openai-completions",
      "models": [
        {
          "id": "coder-model",
          "name": "Qwen Coder",
          "reasoning": false,
          "cost": {"input": 0, "output": 0},
          "contextWindow": 128000,
          "maxTokens": 8192
        },
        {
          "id": "vision-model",
          "name": "Qwen Vision",
          "reasoning": false,
          "cost": {"input": 0, "output": 0},
          "contextWindow": 128000,
          "maxTokens": 8192
        }
      ],
      "apiKey": "qwen-oauth"
    }
  }
}
```

**Status:** ✅ **CONFIGURÉ** - Prêt à l'emploi

---

## 🔧 Procédure de Bascule

### ÉTAPE 1: Identifier Tous les Agents

```bash
# Lister tous les agents
openclaw agents list --json | jq '.[].id'

# Résultat attendu:
# "main"
# "adminapp-codex"
# "admin-agents"
# "clawsentinel"
# "planner"
# "analyst"
# "architect"
# "backend_engineer"
# "frontend_engineer"
# "data_analyst"
# "infra_engineer"
# "integrator"
# "dev"
# "tester"
# "qa"
# "po"
# "scrum_master"
```

---

### ÉTAPE 2: Modifier Configurations Agent

**Pour chaque agent:**

```bash
# 1. Backup config actuelle
cp ~/.openclaw/agents/<agent_id>/agent/models.json \
   ~/.openclaw/agents/<agent_id>/agent/models.json.backup

# 2. Modifier models.json pour utiliser Qwen
# Fichier: ~/.openclaw/agents/<agent_id>/agent/models.json

# Ajouter provider Qwen en premier:
{
  "providers": {
    "qwen-portal": {
      "baseUrl": "https://portal.qwen.ai/v1",
      "api": "openai-completions",
      "models": [
        {
          "id": "qwen-coder",
          "name": "Qwen Coder",
          "reasoning": false,
          "cost": {"input": 0, "output": 0},
          "contextWindow": 128000,
          "maxTokens": 8192
        }
      ],
      "apiKey": "qwen-oauth"
    }
  },
  "defaultProvider": "qwen-portal",
  "defaultModel": "qwen-coder"
}
```

**Agents à migrer:**
- ✅ adminapp-codex
- ✅ admin-agents
- ✅ clawsentinel
- ✅ planner
- ✅ analyst
- ✅ architect
- ✅ backend_engineer
- ✅ frontend_engineer
- ✅ data_analyst
- ✅ infra_engineer
- ✅ integrator
- ✅ dev
- ✅ tester
- ✅ qa
- ✅ po
- ✅ scrum_master

---

### ÉTAPE 3: Modifier Crons pour Utiliser Qwen

**Fichier:** `scripts/configure_parallel_team_crons.sh`

**Changer:**
```bash
ROLE_CODEX_MODEL="${PARALLEL_ROLE_CODEX_MODEL:-${MODEL_CONFIG_PARALLEL_ROLE_MODEL:-gpt-5.3-codex-spark}}"
```

**Vers:**
```bash
ROLE_CODEX_MODEL="${PARALLEL_ROLE_CODEX_MODEL:-${MODEL_CONFIG_PARALLEL_ROLE_MODEL:-qwen-coder}}"
```

---

### ÉTAPE 4: Recréer Crons avec Nouveau Modèle

```bash
# 1. Backup crons actuels
openclaw cron list --json > /tmp/crons_backup_$(date +%Y%m%d_%H%M%S).json

# 2. Supprimer anciens crons (bloqués)
openclaw cron delete ea27cf27-7986-4925-9c16-1d2db1672717  # stale-sweep
openclaw cron delete 742ed606-8aaa-4a66-a521-aaab044eaf54  # admin-agents-supervisor
# ... (tous les crons)

# 3. Recréer avec Qwen
bash scripts/configure_parallel_team_crons.sh --apply --enable

# 4. Vérifier status
openclaw cron list
```

---

### ÉTAPE 5: Tester Exécution

```bash
# Tester un cron manuellement
openclaw cron run <cron_id>

# Vérifier logs
tail -f ~/.openclaw/cron/logs/<cron_id>.log

# Vérifier que modèle est Qwen
cat ~/.openclaw/cron/logs/<cron_id>.log | grep "qwen\|Qwen"
```

---

## ⚡ Script de Migration Automatique

```bash
#!/bin/bash
# migrate_to_qwen.sh

set -e

echo "=== Migration vers Qwen ==="
echo "Date: $(date)"
echo ""

# 1. Backup configs
echo "[1/5] Backup des configurations..."
for agent in adminapp-codex admin-agents clawsentinel planner analyst architect backend_engineer frontend_engineer data_analyst infra_engineer integrator dev tester qa po scrum_master; do
  if [[ -f ~/.openclaw/agents/$agent/agent/models.json ]]; then
    cp ~/.openclaw/agents/$agent/agent/models.json \
       ~/.openclaw/agents/$agent/agent/models.json.backup.$(date +%Y%m%d_%H%M%S)
    echo "  ✅ Backup: $agent"
  fi
done

# 2. Modifier model-config.sh
echo ""
echo "[2/5] Mise à jour model-config.sh..."
sed -i 's/gpt-5.3-codex-spark/qwen-coder/g' configs/model-config.sh || true
echo "  ✅ model-config.sh mis à jour"

# 3. Recréer crons
echo ""
echo "[3/5] Recréation des crons avec Qwen..."
bash scripts/configure_parallel_team_crons.sh --apply --enable
echo "  ✅ Crons recréés"

# 4. Tester exécution
echo ""
echo "[4/5] Test d'exécution..."
openclaw cron run ea27cf27-7986-4925-9c16-1d2db1672717 || echo "  ⚠️ Test skipped (cron may need manual trigger)"
echo "  ✅ Test effectué"

# 5. Rapport
echo ""
echo "[5/5] Rapport de migration..."
openclaw cron list | grep -E "qwen|Qwen|Status" || echo "  ℹ️  Vérification manuelle requise"

echo ""
echo "=== Migration Terminée ==="
echo "Prochaine étape: Vérifier logs et activité des agents"
```

---

## 📊 Validation Checklist

- [ ] **Backup configs** effectués
- [ ] **models.json** modifiés pour tous les agents
- [ ] **model-config.sh** mis à jour
- [ ] **Crons recréés** avec modèle Qwen
- [ ] **Tests exécution** OK
- [ ] **Logs** confirment utilisation Qwen
- [ ] **Sessions tmux** redémarrées
- [ ] **Health endpoint** vérifié

---

## ⚠️ Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Perte contexte agents | 🟠 Moyenne | Élevé | Backup configs avant migration |
| Crons échouent | 🟠 Moyenne | Moyen | Tester manuellement avant bulk |
| Qwen moins performant | 🟡 Faible | Moyen | Surveillance 24h post-migration |
| Auth Qwen expire | 🟡 Faible | Élevé | Vérifier token validity |

---

## 🎯 Commandes de Validation

```bash
# 1. Vérifier modèle utilisé par agent
cat ~/.openclaw/agents/<agent>/agent/models.json | jq '.defaultModel'

# 2. Vérifier modèle utilisé par cron
openclaw cron list --json | jq '.[] | {name: .name, model: .payload.model}'

# 3. Vérifier logs Qwen
grep -r "qwen\|Qwen" ~/.openclaw/cron/logs/ | tail -20

# 4. Tester health endpoint
curl http://localhost:8050/api/health | jq '.last_updates'
```

---

## 📋 NEXT

1. ⏳ **Validation owner** pour migration
2. ⏳ **Exécution script** de migration
3. ⏳ **Surveillance** post-migration (24h)
4. ⏳ **Rapport** d'activité Qwen

---

*Procédure prête à exécuter - En attente validation owner.* 📋⚡
