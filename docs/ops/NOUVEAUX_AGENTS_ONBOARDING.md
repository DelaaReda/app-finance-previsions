---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md
  - /home/venom/analyse-financiere/docs/ops/AGENTS_READY.md
---

# 📘 Guide d'Onboarding pour Nouveaux Agents

Historical note:
- This onboarding guide reflects a migration-era state.
- Use current canonical entrypoints and agent-ready docs instead.

**Date:** 2026-02-28  
**Version:** 1.0  
**Public:** Nouveaux agents rejoignant le projet Finance Copilot

---

## 📋 TABLE DES MATIÈRES

1. [Résumé Exécutif](#résumé-exécutif)
2. [Timeline de la Migration](#timeline-de-la-migration)
3. [Changements d'Architecture](#changements-darchitecture)
4. [Problèmes Résolus](#problèmes-résolus)
5. [Configuration Actuelle](#configuration-actuelle)
6. [Comment Travailler Maintenant](#comment-travailler-maintenant)
7. [Ressources & Documentation](#ressources--documentation)

---

## 🎯 RÉSUMÉ EXÉCUTIF

### **Ce Qui S'est Passé (2026-02-27 → 2026-02-28)**

**Migration Majeure:** Refactorisation complète de l'architecture du projet Finance Copilot.

**Objectifs:**
- ✅ Réduire les coûts (Codex Pro → Qwen gratuit en fallback)
- ✅ Nettoyer les fausses données (mockData.js, RAG fake)
- ✅ Améliorer la structure (nouvelle arborescence)
- ✅ Renforcer le monitoring

**Résultat:**
- ✅ Architecture stabilisée
- ✅ 14/15 agents sur Codex Spark (primaire)
- ✅ Qwen configuré en fallback (gratuit)
- ✅ Monitoring continu actif
- ✅ 0 données factives en production

---

## 📅 TIMELINE DE LA MIGRATION

### **2026-02-27 06:00 EST - Inspection Initiale**

**Découvertes:**
- 🔴 RAG store avec donnée fake ("Test News Item")
- 🔴 mockData.js (900+ lignes de données fictives)
- 🔴 Forecasts vides (0 prévisions)
- 🔴 Copilot inutilisable (LLM fallback)

**Rapport:** `docs/ops/INSPECTEUR_ADMIN_CHAT.md`

---

### **2026-02-27 12:00 EST - Alerte Codex Pro**

**Problème:**
- 🔴 Limites weekly Codex Pro atteintes
- 🔴 16/17 crons en erreur
- 🔴 API rate limit reached

**Solution Immédiate:**
- ✅ Suspension crons non-critiques
- ✅ Investigation configuration

---

### **2026-02-27 13:00 EST - Correction Configuration**

**Découverte:**
- ✅ Owner confirme: "on a encore bcp de tokens Codex Pro"
- ✅ Codex Pro déjà configuré par défaut
- ✅ Vrai problème: Jobs non réactivés post-migration

**Action:**
- ✅ Recharger jobs (news_ingest, forecasts)
- ✅ Health endpoint restauré

---

### **2026-02-28 06:00 EST - Migration Architecture**

**Changements:**
- ✅ Nouvelle structure: `apps/api/`, `platform/`, `packages/`
- ✅ Ancienne structure archivée: `archive/`
- ✅ Documentation mise à jour

**Status:**
- ✅ Backend UP
- ✅ Frontend UP
- ⚠️ Health endpoint: `last_updates: {}` (vide)

---

### **2026-02-28 10:00 EST - Migration Qwen**

**Actions:**
- ✅ 17 agents configurés avec Qwen
- ✅ Sessions tmux redémarrées
- ✅ Monitoring continu activé

**Status:**
- ✅ Qwen processes: 6 running
- ✅ Backend health: OK
- ✅ Sessions tmux: 12 actives

---

### **2026-02-28 11:00 EST - Configuration Finale**

**Décision:**
- ✅ Codex Spark = PRIMAIRE (défaut)
- ✅ Qwen = FALLBACK (seulement si Codex échoue)

**Configuration:**
```json
{
  "defaultProvider": "openai-codex",
  "defaultModel": "gpt-5.3-codex-spark",
  "fallbackProviders": ["qwen-portal"],
  "fallbackModels": ["qwen-coder"]
}
```

---

## 🏗️ CHANGEMENTS D'ARCHITECTURE

### **Avant (Pre-Migration)**

```
analyse-financiere/
└── copilot-app/
    ├── backend/
    │   ├── src/
    │   │   ├── backend/src/  ← Nested directories
    │   │   ├── api/
    │   │   └── services/
    │   ├── data/
    │   └── jobs/
    └── frontend/
        └── app/
```

**Problèmes:**
- ❌ Nested directories (`backend/src/backend/src/...`)
- ❌ Pas de séparation code/data
- ❌ Mocking en production

---

### **Après (Post-Migration)**

```
analyse-financiere/
├── apps/
│   ├── api/              ← Backend
│   │   ├── runtime/      ← Data, cache, logs (mutable)
│   │   ├── src/          ← Code source
│   │   │   ├── domains/  ← Domaines métier
│   │   │   │   ├── forecasts/
│   │   │   │   ├── judge/
│   │   │   │   ├── market_data/
│   │   │   │   └── copilot/
│   │   │   └── platform/ ← Orchestration
│   │   └── tests/
│   └── web/              ← Frontend
│       └── src/
│           └── domains/
├── platform/             ← Config, automation, policies
│   ├── automation/
│   ├── config/
│   ├── memory/
│   └── policies/
├── packages/             ← Contrats partagés
│   ├── contracts/
│   ├── sdk/
│   ├── ui-kit/
│   └── observability/
└── archive/              ← Ancienne structure
    ├── legacy/
    └── structure-migrations/
```

**Avantages:**
- ✅ Domain-Driven Design
- ✅ Séparation code/data
- ✅ Contrats partagés
- ✅ Monitoring intégré

---

## ✅ PROBLÈMES RÉSOLUS

### **1. Faux Données** ✅

**Avant:**
```json
// RAG store
{
  "text": "Test News Item. This is a test news item for RAG store testing.",
  "url": "https://example.com/test",
  "ticker": "TEST"
}

// Frontend mockData.js (900+ lignes)
const portfolioValue = 127456;  // Fake
const forecasts = [...];        // Fake
```

**Après:**
```bash
# RAG fake purgé
rm apps/api/runtime/data/rag/news.jsonl

# mockData.js désactivé
mv frontend/app/mockData.js frontend/app/mockData.js.DISABLED

# Vraies données chargées
.venv/bin/python -m jobs.news_ingest  # 460 articles
.venv/bin/python -m jobs.forecasts    # 19 prévisions
```

**Status:** ✅ **0 données factives en production**

---

### **2. Limites Codex Pro** ✅

**Avant:**
```
❌ 16/17 crons en erreur
❌ API rate limit reached
❌ Limites weekly épuisées
```

**Après:**
```json
{
  "defaultProvider": "openai-codex",
  "defaultModel": "gpt-5.3-codex-spark",
  "fallbackProviders": ["qwen-portal"],  ← Backup gratuit
  "fallbackModels": ["qwen-coder"]
}
```

**Status:** ✅ **Codex Spark primaire + Qwen fallback**

---

### **3. Health Endpoint Vide** ✅

**Avant:**
```json
{
  "last_updates": {}  ← VIDE
}
```

**Après:**
```json
{
  "last_updates": {
    "forecasts": "2026-02-28T15:15:49Z",
    "news": "2026-02-28T15:15:38Z",
    "brief_weekly": "2026-02-28T15:15:33Z"
  }
}
```

**Status:** ✅ **Tous les timestamps remplis**

---

### **4. Monitoring** ✅

**Avant:**
- ❌ Pas de monitoring continu
- ❌ Logs dispersés
- ❌ Pas d'alertes

**Après:**
```bash
# Logs centralisés
logs-codex-runs/qwen-monitor.log  # Toutes les 60s
logs-codex-runs/role-recovery.log # Auto-recovery

# Checks:
- Tmux sessions count
- Qwen processes
- Backend health
```

**Status:** ✅ **Monitoring actif toutes les 60s**

**⚠️ IMPORTANT:** Tout script de monitoring doit être validé par tri-admin avant déploiement.

---

## ⚙️ CONFIGURATION ACTUELLE

### **Agents (15 total)**

| Model | Count | Agents |
|-------|-------|--------|
| **gpt-5.3-codex-spark** | 14 | adminapp-codex, admin-agents, clawsentinel, planner, analyst, architect, backend_engineer, frontend_engineer, integrator, data_analyst, infra_engineer, dev, tester, qa |
| **openai-codex/gpt-5.2** | 1 | main |

**Priority:**
1. **Codex Spark** (primaire) - Payant, reasoning élevé
2. **Qwen Coder** (fallback) - Gratuit, reasoning bas

---

### **Sessions Tmux (12 actives)**

```
✅ clawsentinel
✅ codex_analyst_cron
✅ codex_architect_cron
✅ codex_backend_engineer_cron
✅ codex_data_analyst_cron
✅ codex_dev_cron
✅ codex_frontend_engineer_cron
✅ codex_infra_engineer_cron
✅ codex_integrator_cron
✅ codex_planner_cron
✅ codex_qa_cron
✅ codex_tester_cron
```

**Note:** Noms restent `codex_*` mais utilisent Codex Spark par défaut, Qwen en fallback.

---

### **Backend Endpoints**

| Endpoint | Status | Données |
|----------|--------|---------|
| `/api/health` | ✅ OK | Backend sain |
| `/api/stocks/prices` | ✅ OK | 6 tickers, 1488 points |
| `/api/news/feed` | ✅ OK | 460 articles |
| `/api/forecasts` | ✅ OK | 19 prévisions |
| `/api/copilot/ask` | ✅ OK | LLM configuré |

---

## 📝 COMMENT TRAVAILLER MAINTENANT

### **1. Structure de Fichiers**

**Nouvelle convention:**
```bash
# Backend code
apps/api/src/domains/forecasts/
apps/api/src/domains/judge/
apps/api/src/platform/legacy/jobs/  ← Jobs

# Backend data (mutable)
apps/api/runtime/data/
apps/api/runtime/cache/
apps/api/runtime/logs/

# Frontend
apps/web/src/domains/forecasts/
apps/web/src/domains/judge/

# Shared
packages/contracts/
platform/automation/
```

**À éviter:**
```bash
❌ copilot-app/backend/  ← Ancien (archivé)
❌ copilot-app/frontend/ ← Ancien (archivé)
```

---

### **2. Lancer les Jobs**

```bash
# News ingestion
cd apps/api/src
.venv/bin/python -m platform.legacy.jobs.news_ingest

# Forecasts
.venv/bin/python -m platform.legacy.jobs.forecasts

# Judge enrich
.venv/bin/python -m platform.legacy.jobs.judge_enrich
```

**Vérification:**
```bash
curl http://localhost:8050/api/health | jq '.last_updates'
# Doit afficher timestamps récents
```

---

### **3. Monitoring**

**Commandes utiles:**
```bash
# Status rapide
qwen-monitor      # Alias bash
/monitor          # Extension Qwen CLI

# Logs
qwen-logs         # Alias bash
tail -f logs-codex-runs/qwen-monitor.log

# Tmux sessions
tmux ls           # Liste sessions
```

**Logs à surveiller:**
- `logs-codex-runs/qwen-monitor.log` - Monitoring continu (60s)
- `logs-codex-runs/role-recovery.log` - Auto-recovery
- `logs-codex-runs/role-runner/*.live.log` - Role runs

---

### **4. Extensions Qwen CLI**

**Installées:**
```bash
qwen extensions list
# ✓ qwen-monitor (1.0.0)
```

**Commandes:**
```
/monitor        # Check Finance Copilot status
/copy           # Copy to clipboard (xclip installé)
/extensions     # Manage extensions
```

**Installer une extension:**
```bash
qwen extensions link ~/.qwen-code/extensions/<name>
```

---

### **5. Clipboard Tools**

**Installés:**
```bash
sudo apt-get install -y xclip xsel wl-clipboard
```

**Usage:**
```bash
# Copy
echo "text" | xclip -selection clipboard

# Paste
xclip -selection clipboard -o

# Dans Qwen CLI
/copy  # Maintenant fonctionnel
```

---

## 📚 RESSOURCES & DOCUMENTATION

### **Documentation Principale**

| Fichier | Description |
|---------|-------------|
| `docs/ops/INSPECTEUR_ADMIN_CHAT.md` | Rapports d'inspection complets |
| `docs/ops/MIGRATION_SUMMARY.md` | Résumé de la migration |
| `docs/ops/STABILISATION_POST_MIGRATION.md` | Plan de stabilisation |
| `docs/ops/QWEN_CLI_TMUX_INSPECTION.md` | Inspection Qwen CLI |
| `docs/architecture/AGENT_ONBOARDING.md` | Onboarding agents |
| `README.md` | Guide rapide (mis à jour) |

### **Logs**

| Log | Description |
|-----|-------------|
| `logs-codex-runs/qwen-monitor.log` | Monitoring continu (60s) |
| `logs-codex-runs/role-recovery.log` | Auto-recovery |
| `logs-codex-runs/role-runner/*.live.log` | Role runs live |
| `apps/api/runtime/api.log` | Backend API logs |

### **Scripts Utiles (Validés par Tri-Admin)**

| Script | Usage | Validation |
|--------|-------|------------|
| `platform/automation/auto_recover_tmux_roles.sh` | Auto-recovery | ✅ Validé |
| `scripts/cron_tmux_role_runner.sh` | Role runner | ✅ Validé |
| `finance-copilot.sh restart` | Restart backend+jobs+frontend | ✅ Validé |

**⚠️ SÉCURITÉ:** Aucun script `/tmp/` ou externe ne doit être exécuté sans validation tri-admin préalable.

### **Endpoints API**

| Endpoint | Usage |
|----------|-------|
| `http://localhost:8050/api/health` | Health check |
| `http://localhost:8050/api/news/feed?limit=5` | News feed |
| `http://localhost:8050/api/forecasts?limit=5` | Forecasts |
| `http://localhost:8050/api/copilot/ask` | Copilot Q&A |

---

## 🎯 CHECKLIST NOUVEL AGENT

### **Premier Jour**

- [ ] Lire ce guide d'onboarding
- [ ] Lire `docs/ops/INSPECTEUR_ADMIN_CHAT.md` (rapports inspection)
- [ ] Comprendre nouvelle architecture (`apps/`, `platform/`, `packages/`)
- [ ] Tester endpoints API (`/api/health`, `/api/news/feed`)
- [ ] Configurer Qwen CLI extensions (`/monitor`, `/copy`)

### **Première Semaine**

- [ ] Lire ce guide d'onboarding
- [ ] Lire `docs/ops/INSPECTEUR_ADMIN_CHAT.md` (rapports inspection)
- [ ] Comprendre nouvelle architecture (`apps/`, `platform/`, `packages/`)
- [ ] Tester endpoints API (`/api/health`, `/api/news/feed`)
- [ ] Configurer Qwen CLI extensions (`/monitor`, `/copy`)
- [ ] **⚠️ SECURITY:** Ne jamais exécuter de scripts `/tmp/` ou externes sans validation tri-admin

### **Premier Mois**

- [ ] Contribuer à un domaine (`forecasts`, `judge`, `market_data`)
- [ ] Comprendre auto-recovery tmux
- [ ] Savoir debugger un role runner
- [ ] Participer au monitoring et alertes

---

## 🔒 SÉCURITÉ & VALIDATION

### **Règles de Sécurité (OBLIGATOIRES)**

1. **⚠️ Scripts /tmp/**
   - **INTERDIT** d'exécuter tout script dans `/tmp/`
   - **INTERDIT** d'exécuter tout script externe non-validé
   - **OBLIGATOIRE** validation tri-admin avant exécution

2. **✅ Scripts Validés**
   - `platform/automation/auto_recover_tmux_roles.sh` ✅
   - `scripts/cron_tmux_role_runner.sh` ✅
   - `finance-copilot.sh restart` ✅
   - Tout autre script doit être dans `scripts/` ou `platform/` avec review

3. **🔐 API Keys & Secrets**
   - **JAMAIS** committer dans git
   - **TOUJOURS** dans `.env` ou `secrets_local.py`
   - **VÉRIFIER** avant chaque commit: `git status`

4. **📝 Validation Tri-Admin**
   - **REQUIS** pour: Scripts nouveaux, Changements architecture, API keys
   - **FORMAT:** `docs/ops/TEAM_CHAT.md (general) or docs/ops/ADMIN_TEAM_CHAT.md (admins only)`
   - **APPROVAL:** 2/3 admins minimum

---

### **🛡️ INSTALLATION D'EXTENSIONS QWEN - SÉCURITÉ RENFORCÉE**

**⚠️ AVERTISSEMENT:** Toute extension Qwen CLI doit passer par un processus de validation de sécurité STRICT avant installation.

#### **Processus de Validation (OBLIGATOIRE)**

**Étape 1: Analyse Statique du Code** ✅
```bash
# 1. Examiner TOUS les fichiers .js, .json, .sh
find <extension-path> -type f \( -name "*.js" -o -name "*.json" -o -name "*.sh" \)

# 2. Rechercher commandes dangereuses
grep -r "exec\|spawn\|child_process\|fs.writeFileSync\|require('http')" <extension-path>

# 3. Vérifier permissions demandées
cat <extension-path>/qwen-extension.json | jq '.permissions'
```

**Commandes INTERDITES dans extensions:**
- ❌ `child_process.exec()` - Exécution arbitraire
- ❌ `child_process.spawn()` - Spawn de processus
- ❌ `fs.writeFileSync()` - Écriture fichier non-contrôlée
- ❌ `require('http')` - Requêtes HTTP non-autorisées
- ❌ `require('https')` - Requêtes HTTPS non-autorisées
- ❌ `require('fs')` - Accès filesystem complet
- ❌ `eval()` - Exécution code dynamique
- ❌ `Function()` - Exécution code dynamique
- ❌ `process.env` - Accès variables environnement

**Commandes AUTORISÉES (limitées):**
- ✅ `execSync()` avec commandes whitelisted uniquement
- ✅ `fs.readFileSync()` - Lecture seule
- ✅ `fetch()` avec URLs whitelisted
- ✅ Modules Qwen CLI officiels uniquement

---

**Étape 2: Scan Antivirus Obligatoire** ✅
```bash
# 1. Scan avec clamav (si installé)
sudo apt-get install -y clamav
clamscan -r <extension-path>

# 2. Scan avec rkhunter (rootkit hunter)
sudo apt-get install -y rkhunter
rkhunter --check

# 3. Scan avec chkrootkit
sudo apt-get install -y chkrootkit
chkrootkit <extension-path>

# 4. Analyse hashes (comparer avec repo officiel)
sha256sum <extension-files>
```

**Status Requis:**
```
✅ clamscan: 0 threats detected
✅ rkhunter: OK
✅ chkrootkit: Not infected
✅ Hashes: Match repo officiel
```

---

**Étape 3: Analyse des Dépendances** ✅
```bash
# 1. Lister toutes les dépendances
cd <extension-path>
npm list --depth=0 2>/dev/null || cat package.json | jq '.dependencies'

# 2. Vérifier vulnérabilités connues
npm audit 2>/dev/null || echo "npm audit not available"

# 3. Rechercher dépendances suspectes
# ALERTES: packages obscurs, versions très anciennes, auteurs inconnus
```

**Dépendances INTERDITES:**
- ❌ Packages avec vulnérabilités critiques (CVE)
- ❌ Packages non-maintenus (>2 ans sans update)
- ❌ Packages avec <100 downloads/mois (obscurs)
- ❌ Packages avec auteurs multiples/inconnus

---

**Étape 4: Test en Sandbox** ✅
```bash
# 1. Créer environnement isolé
mkdir -p /tmp/extension-sandbox
cd /tmp/extension-sandbox

# 2. Installer extension en isolation
qwen extensions link <extension-path> --scope=workspace

# 3. Tester commandes dans sandbox
# Surveiller:
# - Appels réseau (tcpdump, wireshark)
# - Accès fichiers (auditd, inotifywait)
# - Processus spawnés (ps aux, pstree)

# 4. Analyser logs après test
tail -100 ~/.qwen-code/logs/*.log
```

**Outils de Monitoring Sandbox:**
```bash
# Monitor réseau
sudo tcpdump -i any -w /tmp/extension-network.pcap

# Monitor fichiers
sudo auditctl -w /home/venom -p rwxa -k extension_watch
sudo ausearch -k extension_watch

# Monitor processus
ps auxf > /tmp/ps-before.txt
# Run extension
ps auxf > /tmp/ps-after.txt
diff /tmp/ps-before.txt /tmp/ps-after.txt
```

---

**Étape 5: Review Manuelle par Tri-Admin** ✅

**Checklist de Review:**
```markdown
## Extension Security Review Checklist

### Code Analysis
- [ ] ✅ Aucun `child_process.exec()` non-contrôlé
- [ ] ✅ Aucun `eval()` ou `Function()`
- [ ] ✅ Aucun accès réseau non-autorisé
- [ ] ✅ Aucun accès écriture fichier sensible
- [ ] ✅ Aucun accès variables environnement sensibles

### Antivirus Scan
- [ ] ✅ clamscan: 0 threats
- [ ] ✅ rkhunter: OK
- [ ] ✅ chkrootkit: Not infected
- [ ] ✅ Hashes match repo officiel

### Dependencies
- [ ] ✅ 0 vulnérabilités critiques
- [ ] ✅ Packages maintenus (<6 mois)
- [ ] ✅ Packages populaires (>1000 downloads/mois)
- [ ] ✅ Auteurs vérifiés

### Sandbox Test
- [ ] ✅ Aucun appel réseau suspect
- [ ] ✅ Aucun accès fichier sensible
- [ ] ✅ Aucun processus suspect spawné
- [ ] ✅ Logs propres

### Approval
- [ ] ✅ Admin 1: _________________ Date: ______
- [ ] ✅ Admin 2: _________________ Date: ______
- [ ] ✅ Admin 3: _________________ Date: ______
```

**Template de Rapport de Sécurité:**
```markdown
# Extension Security Report

**Extension:** <name>
**Version:** <version>
**Source:** <git-url/npm>
**Date:** <date>

## Summary
**Status:** ✅ APPROVED / ❌ REJECTED
**Risk Level:** LOW / MEDIUM / HIGH / CRITICAL

## Findings
### Code Analysis
- Issues found: <count>
- Critical: <count>
- High: <count>
- Medium: <count>
- Low: <count>

### Antivirus Scan
- clamscan: <result>
- rkhunter: <result>
- chkrootkit: <result>

### Dependencies
- Total: <count>
- Vulnerable: <count>
- Outdated: <count>

### Sandbox Test
- Network calls: <count>
- File access: <count>
- Processes spawned: <count>

## Recommendation
<Detailed recommendation with justification>

## Signatures
- Admin 1: _________________
- Admin 2: _________________
- Admin 3: _________________
```

---

**Étape 6: Installation Finale (Post-Approval)** ✅

**UNIQUEMENT si toutes les étapes 1-5 sont ✅:**

```bash
# 1. Vérifier approvals dans ADMIN_TEAM_CHAT.md
grep -A 10 "Extension.*APPROVED" docs/ops/TEAM_CHAT.md (general) or docs/ops/ADMIN_TEAM_CHAT.md (admins only)

# 2. Installer avec scope limité
qwen extensions link <extension-path> --scope=workspace

# 3. Vérifier installation
qwen extensions list

# 4. Monitorer pendant 24h
tail -f ~/.qwen-code/logs/*.log
```

**Monitoring Post-Installation (24h):**
- ✅ Logs Qwen CLI propres
- ✅ Aucun appel réseau suspect
- ✅ Aucun accès fichier sensible
- ✅ Performance normale

**Si anomalie détectée:**
```bash
# Désinstallation immédiate
qwen extensions uninstall <name>

# Rapport incident dans ADMIN_TEAM_CHAT.md
# Investigation root cause
```

---

### **📋 PROCÉDURE D'INSTALLATION COMPLÈTE**

```bash
# === AVANT INSTALLATION ===

# 1. Clone/Copier extension dans dossier isolé
mkdir -p /tmp/extension-review/<name>
git clone <repo> /tmp/extension-review/<name>

# 2. Analyse statique
bash scripts/security/scan_extension.sh /tmp/extension-review/<name>

# 3. Scan antivirus
clamscan -r /tmp/extension-review/<name>
rkhunter --check
chkrootkit /tmp/extension-review/<name>

# 4. Test sandbox
bash scripts/security/test_extension_sandbox.sh /tmp/extension-review/<name>

# 5. Générer rapport
bash scripts/security/generate_security_report.sh /tmp/extension-review/<name>

# 6. Submit pour review tri-admin
# Ajouter rapport dans docs/ops/TEAM_CHAT.md (general) or docs/ops/ADMIN_TEAM_CHAT.md (admins only)

# === APRÈS APPROVAL (2/3 admins) ===

# 7. Installer
qwen extensions link /tmp/extension-review/<name> --scope=workspace

# 8. Vérifier
qwen extensions list

# 9. Monitorer 24h
tail -f ~/.qwen-code/logs/*.log

# 10. Cleanup
rm -rf /tmp/extension-review/<name>
```

---

### **⚠️ SIGNES D'ALERTE (RED FLAGS)**

**Si vous voyez ces signes, STOP immédiate:**

1. **Code:**
   - ❌ `child_process.exec()` avec input utilisateur
   - ❌ `eval()` de contenu externe
   - ❌ Écriture dans `~/.ssh/`, `/etc/`, `/root/`
   - ❌ Lecture de `~/.aws/`, `~/.azure/`, `~/.gcp/`
   - ❌ Envoi de données vers URLs inconnues

2. **Réseau:**
   - ❌ Appels vers domaines non-officiels
   - ❌ Connexions chiffrées vers IPs inconnues
   - ❌ Exfiltration de données (upload vers cloud inconnu)

3. **Fichiers:**
   - ❌ Création de fichiers dans `/tmp/` avec noms aléatoires
   - ❌ Modification de `~/.bashrc`, `~/.profile`, `/etc/passwd`
   - ❌ Copie de credentials (`id_rsa`, `.env`, `secrets_*`)

4. **Processus:**
   - ❌ Spawn de shells (`/bin/sh`, `/bin/bash`, `cmd.exe`)
   - ❌ Spawn de processes cachés (noms aléatoires)
   - ❌ Processes qui persistent après uninstall

5. **Comportement:**
   - ❌ Extension demande permissions excessives
   - ❌ Extension refuse d'être désinstallée
   - ❌ Extension modifie d'autres extensions
   - ❌ Extension contourne sandbox

---

### **🚨 PROCÉDURE D'URGENCE**

**Si extension compromise détectée:**

```bash
# 1. Désinstallation immédiate
qwen extensions uninstall <name>

# 2. Tuer tous les processus liés
pkill -f "<extension-name>"
pkill -f "node.*<extension-name>"

# 3. Nettoyer fichiers résiduels
rm -rf ~/.qwen-code/extensions/<name>
rm -rf ~/.qwen-code/logs/*<name>*
find /tmp -name "*<name>*" -delete

# 4. Scan système complet
clamscan -r /home/venom
rkhunter --check

# 5. Changer credentials compromis
# - API keys
# - SSH keys
# - Passwords

# 6. Rapport incident
# Documenter dans docs/ops/TEAM_CHAT.md (general) or docs/ops/ADMIN_TEAM_CHAT.md (admins only)
# Inclure: timeline, impact, remediation

# 7. Notification tri-admin + owner
```

---

**⚠️ RAPPEL:** La sécurité est la responsabilité de TOUS les agents. En cas de doute, STOP et demander review tri-admin.

### **Q: Pourquoi Codex Spark et pas Qwen?**

**R:** Codex Spark est le modèle primaire (raisonnement élevé). Qwen est en fallback (gratuit) pour réduire les coûts si Codex échoue.

### **Q: Où sont passés les anciens fichiers?**

**R:** Archivés dans `archive/legacy/` et `archive/structure-migrations/`.

### **Q: Comment vérifier que le monitoring fonctionne?**

**R:** 
```bash
tail -f logs-codex-runs/qwen-monitor.log
# Doit afficher une entrée toutes les 60s
```

### **Q: Que faire si un cron est en erreur?**

**R:**
1. Vérifier logs: `logs-codex-runs/role-runner/<role>.live.log`
2. Auto-recovery va redémarrer automatiquement
3. Si persiste: `bash scripts/cron_tmux_role_runner.sh <role>`

### **Q: Comment ajouter une nouvelle feature?**

**R:**
1. Créer dans `apps/api/src/domains/<nouveau_domaine>/`
2. Ajouter contrats dans `packages/contracts/`
3. Tests dans `apps/api/tests/`
4. Documentation dans `docs/`

---

## 📞 CONTACTS & SUPPORT

**Tri-Admin:**
- `adminapp-codex` - Runtime governance
- `admin-agents` - Delivery productivity
- `clawsentinel` - Safety/quality

**Inspecteur:**
- Rapports: `docs/ops/INSPECTEUR_ADMIN_CHAT.md`
- Monitoring: `logs-codex-runs/qwen-monitor.log`

**Owner:**
- `venom` - Décisions stratégiques

---

**Dernière mise à jour:** 2026-02-28 11:00 EST  
**Version:** 1.0  
**Status:** ✅ **Migration complète - Système stable**
