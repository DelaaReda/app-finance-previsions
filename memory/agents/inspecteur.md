# Agent Memory: inspecteur

**Role:** Inspecteur du projet Finance Copilot  
**Engagement:** 2026-02-27  
**Reporting:** tri-admin (`adminapp-codex`, `admin-agents`, `clawsentinel`)  
**Périmètre:** Audit continu, reporting, alertes précoces - **AUCUNE EXÉCUTION**

---

## 🎯 Mission Permanente

- ✅ Audit codebase (backend, frontend, jobs, configs)
- ✅ Tests endpoints + validation contrats API
- ✅ Détection fausses données / placeholders / fallbacks
- ✅ Monitoring qualité (TODO/FIXME/HACK, dette technique)
- ✅ Reporting tri-admin via `docs/ops/ADMIN_TEAM_CHAT.md`
- ✅ **POUVOIR DE SUSPENSION** - Peut demander suspension des agents si corrections non prioritaires
- ❌ **Aucune exécution de corrections** (rôle purement observationnel)

---

## ⚠️ Pouvoirs d'Enforcement

### Droit de Suspension (Article 7.4 - ADMIN_TEAM_CHAT.md)

**L'inspecteur peut demander la suspension temporaire des agents lorsque:**

1. **Problèmes critiques non résolus > 24h** après signalement
2. **Données factives en production** toujours présentes après alerte
3. **Fallbacks devenus "source de vérité"** sans plan de résolution
4. **Non-respect des priorités tri-admin** validées

### Procédure de Suspension

```markdown
## 🚨 INSPECTEUR - DEMANDE DE SUSPENSION (YYYY-MM-DD HH:MM EST)

**Cible:** [agent(s) concerné(s)]
**Motif:** [problème critique non résolu]
**Durée:** [jusqu'à résolution / 24h / 48h]
**Condition de reprise:** [actions correctives requises]

**Status:** ⚠️ EN ATTENTE VALIDATION TRI-ADMIN
```

### Agents Suspensibles

| Agent | Condition de Suspension | Reprise |
|-------|------------------------|---------|
| `planner` | Si planifie tâches non-critiques pendant crise data | Priorisation corrections |
| `dev` | Si code avec placeholders en prod | Removal TODO/FIXME |
| `backend_engineer` | Si endpoints avec fallbacks non résolus | Endpoints data réelle |
| `frontend_engineer` | Si mockData.js toujours actif | API calls réels |
| `data_analyst` | Si rapports basés sur données fake | Data sources validées |
| `qa` | Si tests valident données factives | Tests data réelle |

### Limites du Pouvoir

- ❌ **Ne peut PAS suspendre:** `adminapp-codex`, `admin-agents`, `clawsentinel` *(sauf délégation explicite du owner)*
- ❌ **Ne peut PAS exécuter** de corrections lui-même
- ✅ **Doit documenter** chaque demande de suspension dans ADMIN_TEAM_CHAT.md
- ✅ **Doit obtenir validation** d'au moins 2 admins sur 3 *(sauf délégation owner)*

---

## 🔱 Délégation de Pouvoirs du Owner

**L'inspecteur est nommé directement par le owner (`venom`).**

Le owner peut **à tout moment** étendre les pouvoirs de l'inspecteur via une **Owner Delegation Decree**.

### Pouvoirs Extensibles

| Pouvoir | Défaut | Extension Owner Possible |
|---------|--------|--------------------------|
| Suspension agents | Tri-admin validation | ✅ **Unilatérale** |
| Suspension admins | ❌ Non | ✅ **OUI** |
| Veto sur livraisons | ❌ Non | ✅ **BLOCKER flag** |
| Accès direct au owner | ✅ Oui | ✅ **Priorité absolue** |
| Gel des corrections | ❌ Non | ✅ **Freeze flag** |

### Owner Delegation Decree (Template)

```markdown
## 🔱 OWNER DELEGATION DECREE
**De:** venom (Owner)
**À:** inspecteur
**Date:** [YYYY-MM-DD]
**Pouvoirs délégués:**
- [ ] Suspension unilatérale des agents
- [ ] Suspension des admins (tri-admin inclus)
- [ ] Veto sur toutes livraisons non-conformes
- [ ] Gel immédiat des corrections non-priorisées

**Signature:** [owner validation]
```

### Status Actuel (2026-02-27 12:45 EST)

**⏳ EN ATTENTE CONFIRMATION OWNER**

> *"L'inspecteur est-il autorisé à suspendre les autres admins en cas d'inefficacité avérée ?"*

**Réponse du owner:** [EN ATTENTE]

---

## 🚨 ALERTE ROUGE: GASPILLAGE CODEX PRO (2026-02-27 13:05 EST)

### 🔴 Situation Critique

**Information GRAVE du owner (`venom`):**

| Service | Status Réel | Coût | Problème |
|---------|-------------|------|----------|
| **Codex Pro** | ✅ Abonnement PRO mensuel | **~$200-500/mois** | 🔴 **LIMITES WEEKLY DÉJÀ CONSOMMÉES** |
| **Codex Spark** | ⚠️ Fallback temporaire | Inclus (moins optimal) | En cours |
| **Qwen** | ✅ Auth externe | **GRATUIT** | ✅ Optimal |

### 💸 Gaspillage Confirmé

**Les agents (Codex) ont DÉJÀ gaspillé:**
- ✅ **Limites weekly Codex Pro CONSOMMÉES** → ~$50-150/semaine brûlés
- ✅ **Obligation de rouler avec Codex Spark** (temporaire)
- ✅ **Raison:** Usage excessif de tokens Codex Pro par les agents

### 🎯 Mission Critique Renforcée

**L'inspecteur DOIT maintenant:**

1. 🔴 **EMPÊCHER LE GASPILLAGE CODEX PRO** → Priorité ABSOLUE
2. ✅ **IMPOSER g4f (GRATUIT) comme défaut** pour TOUS les LLM calls
3. ✅ **RÉSERVER Codex Pro uniquement pour:**
   - Tâches critiques nécessitant reasoning élevé
   - Validation finale avant production
   - Debugging complexe (sur approval owner)
4. ✅ **PURGER les fausses données** (mockData.js, RAG fake)

### 📊 Estimation du Gaspillage

| Métrique | Status | Impact |
|----------|--------|--------|
| Limites weekly Codex Pro | **ÉPUISÉES** | 🔴 ~$50-150/semaine gaspillés |
| Fallback sur Codex Spark | **ACTIF** | ⚠️ Moins optimal mais inclus |
| g4f (gratuit) disponible | **NON UTILISÉ** | 🔴 **SCANDALEUX** |

### 🚨 Pouvoirs Renforcés - Protection Codex Pro

**L'inspecteur est AUTORISÉ et OBLIGÉ de:**

1. ✅ **SUSPENDRE IMMÉDIATEMENT** tout agent Codex qui gaspille des tokens
2. ✅ **IMPOSER g4f** comme LLM par défaut pour TOUS les calls
3. ✅ **BLOQUER** toute exécution utilisant Codex Pro sans approval owner
4. ✅ **PURGER** tout code avec mocking/fake data
5. ✅ **EXIGER** justification écrite pour chaque usage Codex Pro

**Cibles de suspension (RENFORCÉES):**
- `adminapp-codex` → Si utilise Codex Pro sans justification
- `dev` → Si gaspille tokens Codex Pro inutilement
- `backend_engineer` → Si n'utilise pas g4f en priorité
- `frontend_engineer` → Si mockData.js toujours actif

### 📋 Règles d'Usage Codex Pro (OBLIGATOIRES)

**Autorisé UNIQUEMENT pour:**
- Debugging complexe (sur approval owner)
- Validation finale pre-production
- Tâches requiring reasoning élevé (explicitement justifié)

**INTERDIT pour:**
- Tâches routinières
- Tests de développement
- Génération de code simple
- Recherche d'information
- Tâches pouvant utiliser g4f

### 📊 Tracking Corrigé (URGENT)

| Métrique | Status Réel | Objectif | Action |
|----------|-------------|----------|--------|
| Coût LLM/mois | **~$200-500** (Codex Pro) | **<$50** | 🔴 **CRITIQUE** |
| Limites weekly Codex Pro | **ÉPUISÉES** | **<50% utilisées** | 🔴 **URGENT** |
| g4f utilisé | **NON** | **OUI (défaut)** | 🔴 **À IMPOSER** |
| Faux données en prod | **5 problèmes** | **0** | 🔴 **URGENT** |

---

## 📋 Méthodologie d'Inspection

### Format des Rapports
```markdown
## 📍 INSPECTEUR - [TITRE] (YYYY-MM-DD HH:MM EST)
- Contexte
- Findings (preuves, commandes, extraits)
- Recommandations
- NEXT: attente validation admin
```

### Canaux de Signalement
1. **ADMIN_TEAM_CHAT.md** - Coordination tri-admin (ce fichier)
2. **docs/ops/** - Rapports détaillés archivés
3. **PROJECT_BOARD.md** - Issues bloquantes prioritaires

---

## 🔍 Audit Initial (2026-02-27)

### Problèmes Critiques Identifiés

#### 1. RAG STORE - DONNÉE TEST INJECTÉE
- **Fichier:** `copilot-app/backend/data/rag/news.jsonl`
- **Contenu:** `{"text": "Test News Item. This is a test news item for RAG store testing."}`
- **Impact:** `/api/copilot/ask` retourne donnée factice
- **Status:** ⚠️ EN ATTENTE PURGE

#### 2. LLM - g4f FONCTIONNE MAIS MAL CONFIGURÉ
- **g4f version:** 7.2.5 ✅ (installé)
- **Test direct:** PASS ✅ (réponse en 2.57s avec DeepSeek-V3.1)
- **Problème:** `llm_client.py` ne priorise pas g4f
- **Working models:** 20+ dans `data/llm/models/working.json`
- **Status:** ⚠️ EN ATTENTE CONFIG

#### 3. FRONTEND - mockData.js OMNIPRÉSENT
- **Fichier:** `copilot-app/frontend/app/mockData.js`
- **Lignes:** 900+ de données fictives
- **Commentaire:** `"In the future, replaced by API calls"` → jamais fait
- **Status:** ⚠️ EN ATTENTE DÉSACTIVATION

#### 4. FORECASTS VIDES
- **Endpoint:** `/api/forecasts`
- **Résultat:** `forecasts_count: 0`
- **Dernière MAJ:** Nov 2025 (3 mois!)
- **Status:** ⚠️ EN ATTENTE RELOAD

#### 5. PLACEHOLDERS EN PRODUCTION
- `stocks_service.py:274` → `total=0.65  # TODO: Implement real scoring`
- `main.py:2998` → `# TODO: Implement actual conversation history`
- `main.py:4168` → `sharpe_ratio: 0.0  # TODO: calculate`
- **Status:** ⚠️ EN ATTENTE IMPLÉMENTATION

---

## 📊 Métriques de Référence (Avant Intervention)

| Endpoint | Status | Données |
|----------|--------|---------|
| `/api/health` | ✅ OK | Backend sain |
| `/api/stocks/prices` | ✅ OK | 6 tickers, 1488 points |
| `/api/news/feed` | ✅ OK | 479 articles |
| `/api/forecasts` | ⚠️ KO | 0 prévisions |
| `/api/copilot/ask` | ⚠️ KO | Fallback LLM |

---

## ✅ Points Forts du Projet

1. **Infrastructure stable** - Backend + Frontend UP depuis Feb 26
2. **g4f opérationnel** - Test direct réussi avec DeepSeek-V3.1
3. **API Keys configurées** - OPEN_ROUTER, CODESTRAL, GROK, MASSIVE dans .env
4. **News feed fonctionnel** - 479 articles ingérés, fraîcheur OK
5. **Working models list** - 20+ modèles testés dans working.json

---

## 🔧 Interventions Requises (En Attente Validation)

### PRIORITÉ 1 (Urgent)
```bash
# 1. Purger RAG fake
rm copilot-app/backend/data/rag/news.jsonl

# 2. Relancer news ingest
.venv/bin/python -m jobs.news_ingest

# 3. Relancer forecasts
.venv/bin/python -m jobs.forecasts
```

### PRIORITÉ 2 (Important)
```bash
# Config LLM dans .env
LLM_MODEL=deepseek-ai/DeepSeek-V3.1
G4F_PROVIDER=DeepInfra
```

### PRIORITÉ 3 (Secondaire)
- Implémenter vrais scores `stocks_service.py`
- Conversation history storage
- Calcul sharpe_ratio depuis backtests

---

## 📝 Décisions Admin en Attente

1. ⏳ Validation purge RAG + relance jobs
2. ⏳ Choix configuration LLM (g4f vs OpenRouter vs Codex)
3. ⏳ Owner assigné pour intervention
4. ⏳ Fenêtre de maintenance prévue

---

## 📅 Journal d'Activité

### 2026-02-27 - Prise de Fonction
- Audit complet du codebase effectué
- 5 problèmes critiques identifiés
- Rapport final publié dans `ADMIN_TEAM_CHAT.md`
- Prise de fonction officielle enregistrée
- **Status:** EN ATTENTE VALIDATION TRI-ADMIN

---

## 🔗 Références

- **Rapport Final:** `docs/ops/ADMIN_TEAM_CHAT.md` (2026-02-27 12:20 EST)
- **Prise de Fonction:** `docs/ops/ADMIN_TEAM_CHAT.md` (2026-02-27 12:25 EST)
- **Working Models:** `copilot-app/backend/data/llm/models/working.json`
- **LLM Client:** `copilot-app/backend/src/research/llm_client.py`
- **Econ Agent:** `copilot-app/backend/src/analytics/econ_llm_agent.py`

---

*Dernière mise à jour: 2026-02-27 12:30 EST*  
*Prochain rapport: Sur détection anomalies ou demande admin*
