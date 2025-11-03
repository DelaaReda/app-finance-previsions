# AGENTS.MD - GUIDE DE DÉPLOIEMENT FINANCE COPILOT

## 🎯 BUT DU DOCUMENT

Ce guide est destiné à tous les agents/devs travaillant sur **Finance Copilot**.
Ici, tout est **réel** : pas de mocks, pas de shortcuts.
Si quelque chose ne marche pas → **on le règle**, on ne le masque pas.

Ce projet veut refléter la réalité marché / manipulation vraie data.
Donc **pas de données simulées**.

---

## 🚨 RÈGLES FONDAMENTALES

### ✅ TOUJOURS LANCER LE PROJET AVEC LE SCRIPT FOURNI

Pour éviter :

* plusieurs serveurs backend en parallèle
* conflits de ports (5173 / 8050)
* erreurs d’environnement
* pertes de logs

Obligatoire :

```bash
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start
```

Et pour arrêter proprement :

```bash
/Users/venom/Documents/analyse-financiere/finance-copilot.sh stop
```

> Personne ne doit lancer `uvicorn`, `npm run dev`, `docker`, etc. directement.
> Le script gère **tout l’environnement dev standardisé**.

---

## 📂 STRUCTURE ACTUELLE DU PROJET

```
analyse-financiere/
├── finance-copilot.sh          # Script officiel start/stop (lien vers copilot-app/copilot.sh)
├── copilot-app/                # Application principale Finance Copilot
│   ├── backend/               # Backend Python (API FastAPI)
│   │   ├── api/   
│   │   │   ├── main.py        # Entrée FastAPI
│   │   │   ├── routes/        # Endpoints organisés
│   │   │   └── services/      # Logic de marché, AI, etc.
│   │   ├── models/            # ML/forecasting logic
│   │   ├── requirements.txt
│   │   └── run_api.py         # Script de démarrage backend
│   ├── frontend/
│   │   └── webapp/            # Frontend React/Vite
│   │       ├── src/
│   │       │   ├── api/
│   │       │   │   └── client.ts    # API client avec gestion des erreurs
│   │       │   ├── pages/
│   │       │   ├── components/
│   │       │   └── hooks/
│   │       ├── package.json
│   │       ├── vite.config.ts # Proxy API backend
│   │       └── .env           # VITE_API_BASE_URL
│   ├── scripts/               # Scripts de gestion système
│   │   ├── start.sh
│   │   ├── stop.sh
│   │   ├── test_system.sh
│   │   └── ...
│   └── docs/                  # Documentation
└── agent-stack-oss/           # Agent OSS (projet séparé)
    └── ...
```

---

## ✅ SITUATION ACTUELLE - APPLICATION OPÉRATIONNELLE

### Backend API (http://localhost:8050)
Tous les endpoints sont maintenant **opérationnels** :

| Endpoint | Statut | Réponse |
|----------|--------|---------| 
| `/api/health` | ✅ OK | JSON avec `{"ok": true, ...}` |
| `/api/macro/series` | ✅ OK | Données FRED (CPI, VIX, etc.) |
| `/api/stocks/prices` | ✅ OK | Données yfinance (SPY, QQQ, etc.) |
| `/api/news/feed` | ✅ OK | Flux RSS avec scores |
| `/api/brief/daily` | ✅ OK | Brief quotidien avec signaux/risques |
| `/api/brief/weekly` | ✅ OK | Brief hebdomadaire |
| `/api/forecasts` | ✅ OK | Prévisions (vides si pas de données) |
| `/api/dashboard/kpis` | ✅ OK | Indicateurs KPI |
| `/api/copilot/ask` | ✅ OK | Interface LLM |

### Frontend UI (http://localhost:5173) 
Toutes les pages sont **accessibles** avec données :

| Page | Statut | Fonctionnalité |
|------|--------|----------------|
| `/` (Dashboard) | ✅ OK | Vue d'ensemble complète |
| `/brief` (Market Brief) | ✅ OK | Briefs avec top 3 signaux/risques |
| `/macro` | ✅ OK | Données macroéconomiques |
| `/stocks` | ✅ OK | Prix et indicateurs boursiers |
| `/news` | ✅ OK | Flux d'actualités |
| `/copilot` | ✅ OK | Interface LLM avec Q&A |
| `/forecasts` | ✅ OK | Page de prévisions |
| `/backtests` | ✅ OK | Page de backtests |
| `/judge` | ✅ OK | LLM Judge |

---

## 🔧 CORRECTIONS RÉCENTES APPLIQUÉES

### 1. Problème de routage API résolu
**Avant** : Le frontend appelait `http://localhost:5173/api/...` mais les endpoints backend étaient sur `http://localhost:8050/api/...`
**Solution** : Mise en place du proxy Vite dans `copilot-app/frontend/webapp/vite.config.ts` :
```ts
proxy: {
  '/api': {
    target: 'http://localhost:8050',
    changeOrigin: true,
    secure: false,
  },
  '/health': {
    target: 'http://localhost:8050',
    changeOrigin: true,
    secure: false,
  }
}
```

### 2. Variable d'environnement corrigée
**Avant** : `VITE_API_BASE_URL` dans `.env` mais pas prise en charge
**Solution** : Mise à jour du fichier `.env` dans `copilot-app/frontend/webapp/` avec :
```
VITE_API_BASE_URL=http://localhost:8050
```

### 3. Gestion des erreurs backend
**Avant** : Certains endpoints backend renvoyaient des erreurs ou `null` 
**Solution** : Tous les endpoints renvoient maintenant des structures JSON valides :
- Tableaux vides `[]` au lieu de `null`
- Objets avec structure définie
- Gestion appropriée des exceptions

---

## 🌐 API & NETWORKING RULES

### Base URL (dev local)

Dans `copilot-app/frontend/webapp/src/api/client.ts` :

```ts
const API_BASE = (import.meta.env as any).VITE_API_BASE_URL ?? "/api";
```

### Ports standards

| Service           | Port   | Obligatoire |
| ----------------- | ------ | ----------- |
| Frontend (Vite)   | `5173` | ✅           |
| Backend (FastAPI) | `8050` | ✅           |

> Si votre terminal, Machine, VSCode, Docker ou Node démarre sur un autre port = **erreur**.

---

## 🧪 PROCESS DE MISE EN ROUTE

### 1) Démarrer tout

```bash
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start
```

### 2) Vérifier backend

```bash
curl http://localhost:8050/api/health
```

### 3) Vérifier front

Ouvrir :

```
http://localhost:5173
```

### 4) Vérifier l'état complet

```bash
/Users/venom/Documents/analyse-financiere/finance-copilot.sh status
```

---

## 🩺 TROUBLESHOOTING OFFICIEL

### ✅ Le front ne charge aucune donnée ?

→ Vérifiez que le backend tourne :
```bash
curl http://localhost:8050/api/health
```

### ✅ Pages en "loading" infini ?

→ Endpoint backend inexistant ou erreur de parsing
→ Vérifiez dans les DevTools → Network si les appels API échouent

### ✅ Erreur JS `undefined.length`

→ Le backend n’a pas renvoyé un tableau réel
→ Corriger API pour garantir structure de données cohérente

### ✅ Routes 404 pour endpoints existants

→ Le proxy Vite peut ne pas fonctionner
→ Vérifiez `copilot-app/frontend/webapp/vite.config.ts`

---

## 🧪 TESTS DE FONCTIONNALITÉ

### Vérification des endpoints backend :
```bash
curl http://localhost:8050/api/health
curl http://localhost:8050/api/macro/series
curl http://localhost:8050/api/stocks/prices?ticker=SPY
curl http://localhost:8050/api/news/feed
curl http://localhost:8050/api/brief/daily
curl http://localhost:8050/api/forecasts
```

### Vérification via proxy frontend :
```bash
curl http://localhost:5173/api/health
curl http://localhost:5173/api/macro/series
curl http://localhost:5173/api/stocks/prices?ticker=SPY
curl http://localhost:5173/api/news/feed
curl http://localhost:5173/api/brief/daily
curl http://localhost:5173/api/forecasts
```

---

## 🚀 URLS DISPONIBLES

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend UI** | http://localhost:5173 | Interface utilisateur principale |
| **Backend API** | http://localhost:8050 | API backend FastAPI |
| **Documentation API** | http://localhost:8050/docs | Swagger UI |
| **BrowserMCP** | http://localhost:9009 | Serveur d'automatisation browser |

---

## 🚫 INTERDICTIONS

| Action | Statut |
|--------|--------| 
| Lancer des serveurs localement "à la main" | ❌ |
| Changer les ports standardisés | ❌ |
| Mettre des données mockées | ❌ |
| Pousser du code non testé via les scripts | ❌ |
| Créer des fichiers à la racine du repo | ❌ |

---

## ✅ CULTURE PROJET

> Ce projet = discipline dev + vérité marché.

**On ne masque pas les erreurs**
- On identifie les vraies causes
- On corrige les vrais problèmes
- On ne contourne pas les bugs

**On ne fait pas de "front vide"**
- On assure la liaison backend ↔ frontend
- On fournit des données réelles à toutes les couches
- On ne simule pas l'information

**On ne "fake pas pour que ça passe"**
- On implémente les vrais endpoints
- On connecte les vraies sources de données
- On teste les vraies fonctionnalités

---

## 🧠 COMMANDES UTILES

### Trouver processus sur ports
```bash
lsof -i :8050
lsof -i :5173
kill -9 <PID>
```

### Arrêter tous les services proprement
```bash
./finance-copilot.sh stop
```

### Voir les logs backend
```bash
tail -f api.log
```

### Voir les logs frontend
```bash
tail -f copilot-app/frontend/webapp/frontend.log
```

---

## 🧵 WORKFLOW DE CONTRIBUTION

1. **Pull la branche** - `git pull origin main`
2. **Lancer via script** - `./finance-copilot.sh start`
3. **Tester l'UI** - Vérifier que les pages affichent des données
4. **Vérifier les endpoints** - S'assurer que les APIs répondent
5. **Déboguer** - Pas de mock, correction des vrais problèmes
6. **Implémentation réelle** - Connecter les vraies données/sources
7. **Test UI final** - S'assurer que l'utilisateur final peut utiliser la fonctionnalité
8. **Commit + Push** - Avec documentation si nécessaire

---

## 📊 INDICATEURS DE SANTÉ

- **Taux de couverture** : >90% des tickers ≤ 24h
- **Fraîcheur news** : Médiane < 10 minutes  
- **Sources** : ≥ 2 citations pour chaque réponse LLM
- **Performance** : Réponses < 2 secondes
- **Robustesse** : Gestion des erreurs et fallbacks
- **Disponibilité** : Backend et frontend répondent
- **Connectivité** : Tous les endpoints critiques fonctionnent

---

## 🔍 VÉRIFICATIONS AVANT DÉPLOIEMENT

- [ ] Backend API fonctionnel (tous les endpoints répondent)
- [ ] Frontend UI accessible (toutes les pages chargent)
- [ ] Données réelles affichées (pas de mocks)
- [ ] Tests système passent (`./finance-copilot.sh test`)
- [ ] Proxy API correctement configuré
- [ ] Gestion des erreurs mise en place
- [ ] Documentation à jour
- [ ] Scripts de gestion fonctionnels

---

## 🎯 OBJECTIF FINAL

**Finance Copilot est maintenant ENTIEREMENT OPERATIONNEL** avec :

✅ Backend stable - API FastAPI avec tous les endpoints critiques  
✅ Frontend fonctionnel - Interface React complète avec navigation  
✅ Communication correcte - Proxy API en place pour le développement  
✅ Structure de données - Contrats API cohérents (aucun null non géré)  
✅ Gestion des erreurs - Fallbacks et erreurs capturées  
✅ Documentation - Guides et procédures mises à jour  
✅ BrowserMCP - Serveur d'automatisation opérationnel  

L'application est prête pour une utilisation en production et peut être étendue avec de nouvelles fonctionnalités ou améliorée avec des données réelles provenant de sources variées. 🚀



## ✅ SITUATION ACTUELLE

### Backend API (http://localhost:8050)
Tous les endpoints sont maintenant **opérationnels** :

| Endpoint | Statut | Réponse |
|----------|--------|---------| 
| `/api/health` | ✅ OK | JSON avec `{"ok": true, ...}` |
| `/api/macro/series` | ✅ OK | Données FRED (CPI, VIX, etc.) |
| `/api/stocks/prices` | ✅ OK | Données yfinance (SPY, QQQ, etc.) |
| `/api/news/feed` | ✅ OK | Flux RSS avec scores |
| `/api/brief/daily` | ✅ OK | Brief quotidien avec signaux/risques |
| `/api/brief/weekly` | ✅ OK | Brief hebdomadaire |
| `/api/forecasts` | ✅ OK | Prévisions (vides si pas de données) |
| `/api/dashboard/kpis` | ✅ OK | Indicateurs KPI |

### Frontend UI (http://localhost:5173) 
Toutes les pages sont **accessibles** avec données :

| Page | Statut | Fonctionnalité |
|------|--------|----------------|
| `/` (Dashboard) | ✅ OK | Vue d'ensemble complète |
| `/brief` (Market Brief) | ✅ OK | Briefs avec top 3 signaux/risques |
| `/macro` | ✅ OK | Données macroéconomiques |
| `/stocks` | ✅ OK | Prix et indicateurs boursiers |
| `/news` | ✅ OK | Flux d'actualités |
| `/copilot` | ✅ OK | Interface LLM avec Q&A |
| `/forecasts` | ✅ OK | Page de prévisions |
| `/backtests` | ✅ OK | Page de backtests |
| `/judge` | ✅ OK | LLM Judge |

## 🔧 CORRECTIONS APPLIQUÉES

### 1. Problème de routage API
**Avant** : Le frontend appelait `http://localhost:5173/api/...` mais les endpoints backend étaient sur `http://localhost:8050/api/...`
**Solution** : Mise en place du proxy Vite dans `vite.config.ts` :
```ts
proxy: {
  '/api': {
    target: 'http://localhost:8050',
    changeOrigin: true,
    secure: false,
  },
  '/health': {
    target: 'http://localhost:8050',
    changeOrigin: true,
    secure: false,
  }
}
```

### 2. Variable d'environnement
**Avant** : `VITE_API_BASE_URL` dans `.env` mais pas prise en charge
**Solution** : Mise à jour du fichier `.env` dans `webapp/` avec :
```
VITE_API_BASE_URL=http://localhost:8050
```

### 3. Gestion des erreurs
**Avant** : Certains endpoints backend renvoyaient des erreurs ou `null` 
**Solution** : Tous les endpoints renvoient maintenant des structures JSON valides :
- Tableaux vides `[]` au lieu de `null`
- Objets avec structure définie
- Gestion appropriée des exceptions

## 🧪 TESTS COMPLÉMENTAIRES

### Vérification des endpoints backend :
```bash
curl http://localhost:8050/api/health
curl http://localhost:8050/api/macro/series
curl http://localhost:8050/api/stocks/prices?ticker=SPY
curl http://localhost:8050/api/news/feed
curl http://localhost:8050/api/brief/daily
curl http://localhost:8050/api/forecasts
```

### Vérification via proxy frontend :
```bash
curl http://localhost:5173/api/health
curl http://localhost:5173/api/macro/series
curl http://localhost:5173/api/stocks/prices?ticker=SPY
curl http://localhost:5173/api/news/feed
curl http://localhost:5173/api/brief/daily
curl http://localhost:5173/api/forecasts
```

## 🚀 DÉMARRAGE DE L'APPLICATION

### Via scripts (recommandé) :
```bash
# Démarrer l'application complète
./finance-copilot.sh start

# Arrêter l'application
./finance-copilot.sh stop

# Redémarrer
./finance-copilot.sh restart

# Vérifier l'état
./finance-copilot.sh status
```

### URLs disponibles :
- **Frontend UI** : http://localhost:5173
- **Backend API** : http://localhost:8050
- **Documentation API** : http://localhost:8050/docs
- **BrowserMCP** : http://localhost:9009

## 🎯 FONCTIONNALITÉS COMPLÈTES

✅ **Dashboard** - Vue d'ensemble avec filtres et indicateurs  
✅ **Market Briefs** - Briefs quotidiens et hebdomadaires  
✅ **5 Piliers** - Tous fonctionnels (Macro, Stocks, News, Copilot, Brief)  
✅ **Analyse** - Prévisions, backtests, alerts  
✅ **Outils LLM** - Copilot et Judge  
✅ **Interface utilisateur** - Navigation complète entre toutes les pages  
✅ **BrowserMCP** - Serveur d'automatisation prêt pour les modèles IA  

## 📊 INDICATEURS DE SANTÉ

- **Taux de couverture** : >90% des tickers ≤ 24h
- **Fraîcheur news** : Médiane < 10 minutes
- **Sources** : ≥ 2 citations pour chaque réponse LLM
- **Performance** : Réponses < 2 secondes
- **Robustesse** : Gestion des erreurs et fallbacks

---

## 👨‍💻 MESSAGE AUX DÉVELOPPEURS

Finance Copilot est maintenant **entièrement opérationnel** avec :

1. **Backend stable** - API FastAPI avec tous les endpoints critiques
2. **Frontend fonctionnel** - Interface React complète avec navigation
3. **Communication correcte** - Proxy API en place pour le développement
4. **Structure de données** - Contrats API cohérents (aucun `null` non géré)
5. **Gestion des erreurs** - Fallbacks et erreurs capturées
6. **Documentation** - Guides et procédures mises à jour