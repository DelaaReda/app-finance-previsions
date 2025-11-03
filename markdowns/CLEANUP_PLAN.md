# 🧹 PLAN DE NETTOYAGE DU REPOSITORY PRINCIPAL

## 🎯 OBJECTIF
Nettoyer et organiser le repository principal pour refléter la nouvelle structure avec des projets bien séparés.

## ✅ CE QUI RESTE DANS LE REPOSITORY PRINCIPAL

### 📁 Dossiers à conserver
```
analyse-financiere/
├── .git/                    ← Historique Git (indispensable)
├── .github/                 ← Configuration GitHub
├── agent-stack-oss/         ← Projet Agent OSS (séparé)
├── copilot-app/             ← Application Finance Copilot principale
└── tools/                   ← Outils de développement
```

### 📄 Fichiers à conserver
```
analyse-financiere/
├── .gitignore              ← Filtres Git
├── .env.sample            ← Template variables d'environnement
├── copilot.sh             ← Script principal d'orchestration
├── Makefile               ← Commandes de développement
├── README.md              ← Documentation principale
├── requirements.txt       ← Dépendances racine (si nécessaire)
└── requirements-api*.txt  ← Spécifications API (si pertinent)
```

## ❌ CE QUI DOIT ÊTRE SUPPRIMÉ

### 📁 Dossiers obsolètes
```
❌ __pycache__/              ← Cache Python à ignorer via .gitignore
❌ .pytest_cache/            ← Cache tests à ignorer via .gitignore
❌ .venv/                    ← Environnement virtuel racine (NON À CONSERVER)
❌ venv/                     ← Environnement virtuel alternatif (NON À CONSERVER)
❌ node_modules/             ← Dépendances Node.js à ignorer via .gitignore
❌ logs/                     ← Logs à ignorer via .gitignore
❌ cache/                     ← Cache à ignorer via .gitignore
❌ artifacts/                ← Artifacts à ignorer via .gitignore
❌ data/                     ← Données à ignorer via .gitignore
❌ integration/              ← À déplacer si pertinent
❌ ops/                      ← À déplacer si pertinent
❌ queries/                  ← À déplacer si pertinent
❌ tests/                    ← À déplacer si pertinent
❌ webapp/                   ← Ancien frontend (maintenant dans copilot-app/frontend/)
```

### 📄 Fichiers obsolètes
```
❌ api.log                  ← Logs backend (à ignorer via .gitignore)
❌ =0.31.1                  ← Fichiers temporaires
❌ =2.11.0                  ← Fichiers temporaires
❌ localhost.har            ← Fichiers de debug navigateur
❌ *.pyc                     ← Fichiers compilés Python (à ignorer via .gitignore)
❌ .DS_Store               ← Fichiers système macOS (à ignorer via .gitignore)
```

## 🏗️ ORGANISATION CORRECTE PAR PROJET

### Structure `copilot-app/` (Application Finance Copilot)
```
copilot-app/
├── backend/               ← Backend Python FastAPI
│   ├── api/               ← Points d'entrée API
│   ├── src/               ← Code source métier
│   ├── run_api.py         ← Point d'entrée backend
│   ├── api.log            ← Logs backend
│   └── .venv/             ← Environnement virtuel Python backend
├── frontend/              ← Frontend React/Vite
│   └── webapp/            ← Application web
│       ├── src/           ← Code source frontend
│       ├── frontend.log   ← Logs frontend
│       └── node_modules/   ← Dépendances Node.js
├── scripts/               ← Scripts de gestion système
│   ├── start.sh          ← Démarrage application
│   ├── stop.sh           ← Arrêt application
│   └── test_system.sh     ← Tests système
└── docs/                 ← Documentation projet
    └── README_SCRIPTS.md  ← Guide utilisation scripts
```

### Structure `agent-stack-oss/` (Agent OSS)
```
agent-stack-oss/
├── src/                   ← Code source agent
├── training-materials/    ← Matériaux formation
├── .venv/                 ← Environnement virtuel Python agent
└── ...                    ← Autres fichiers agent
```

## 🔧 DÉCISIONS IMPORTANTES

### 1. Environnements Virtuels
**❓ Doit-on conserver les environnements virtuels dans le repository ?**
**❌ NON** - Les environnements virtuels doivent être ignorés via `.gitignore`
- Chaque développeur doit créer son propre environnement
- Les dépendances sont définies dans `requirements.txt`
- Cela évite les conflits de versions et réduit la taille du repository

### 2. Dépendances Node.js
**❓ Doit-on conserver `node_modules/` dans le repository ?**
**❌ NON** - Les dépendances Node.js doivent être ignorées via `.gitignore`
- Chaque développeur doit exécuter `npm install` pour installer les dépendances
- Les versions sont définies dans `package.json` et `package-lock.json`
- Cela évite les conflits et réduit la taille du repository

### 3. Logs et Données
**❓ Doit-on conserver les logs et données dans le repository ?**
**❌ NON** - Les logs et données doivent être ignorés via `.gitignore`
- Les logs sont générés à l'exécution
- Les données peuvent être récupérées via les sources officielles
- Cela évite de polluer le repository avec des fichiers volumineux

## ✅ ACTIONS À RÉALISER

### Phase 1 : Nettoyage immédiat
1. Supprimer les environnements virtuels obsolètes du repository principal
2. Mettre à jour `.gitignore` pour ignorer correctement les fichiers générés
3. Déplacer les fichiers de documentation pertinents dans les bons dossiers
4. Supprimer les fichiers temporaires et caches

### Phase 2 : Mise à jour documentation
1. Mettre à jour le README.md principal avec la nouvelle structure
2. Créer un guide pour les autres agents sur les bonnes pratiques
3. Documenter clairement ce qui doit être créé/où pour chaque projet

### Phase 3 : Validation
1. Vérifier que tous les services démarrent correctement
2. S'assurer que les scripts de gestion fonctionnent
3. Confirmer que le repository est propre et bien organisé

## 📋 LISTE DE VÉRIFICATION

- [ ] Environnements virtuels supprimés du repository
- [ ] Fichiers générés ignorés via `.gitignore`
- [ ] Structure de dossiers conforme à l'organisation par projet
- [ ] Documentation mise à jour et organisée
- [ ] Scripts de gestion fonctionnels
- [ ] Services démarrant correctement
- [ ] Repository propre et maintenable