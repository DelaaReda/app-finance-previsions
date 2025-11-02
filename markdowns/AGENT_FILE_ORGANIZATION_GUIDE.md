# 📁 GUIDE POUR LES AGENTS - ORGANISATION DES FICHIERS

## 🎯 STRUCTURE DU PROJET

Ce repository contient deux projets principaux distincts :

```
analyse-financiere/
├── copilot-app/              ← Application Finance Copilot (APPLICATION PRINCIPALE)
│   ├── backend/             ← Backend Python (API)
│   ├── frontend/            ← Frontend React/Vite
│   ├── scripts/             ← Scripts de gestion système
│   └── docs/               ← Documentation application
├── agent-stack-oss/         ← Agent OSS (PROJET SÉPARÉ)
│   ├── src/                ← Code source agent
│   ├── training-materials/ ← Matériaux de formation
│   └── ...                 ← Autres fichiers agent
└── copilot.sh              ← Script principal (racine)
```

## 📍 OÙ CRÉER VOS FICHIERS - GUIDE PAR PROJET

### 🎯 SI VOUS TRAVAILLEZ SUR L'APPLICATION FINANCE COPILOT

**EMPLACEMENT CORRECT :** `/copilot-app/`

#### 📁 Structure recommandée :
```
copilot-app/
├── backend/                 ← Pour le code backend Python
│   ├── api/                ← Endpoints API
│   ├── src/                ← Services et logique métier
│   ├── tests/              ← Tests unitaires backend
│   └── docs/              ← Documentation backend
├── frontend/               ← Pour le code frontend React
│   └── webapp/            ← Application web
│       ├── src/           ← Composants React
│       ├── components/    ← Composants réutilisables
│       ├── hooks/         └── Hooks personnalisés
│       ├── services/      └── Services API
│       ├── types/         └── Types TypeScript
│       └── utils/         └── Fonctions utilitaires
├── scripts/                ← Pour les scripts de gestion
│   ├── deploy/            ← Scripts de déploiement
│   ├── maintenance/       └── Scripts de maintenance
│   └── utils/             └── Scripts utilitaires
└── docs/                  ← Pour la documentation
    ├── architecture/      ← Diagrammes et architecture
    ├── api/               └── Documentation API
    ├── guides/            └── Guides d'utilisation
    └── tutorials/         └── Tutoriels
```

#### 📄 Exemples de création de fichiers :
```bash
# ✅ BON : Créer un nouveau service backend
touch copilot-app/backend/src/new_service.py

# ✅ BON : Créer un nouveau composant frontend
touch copilot-app/frontend/webapp/src/components/NewComponent.tsx

# ✅ BON : Créer un script de déploiement
touch copilot-app/scripts/deploy/new_deploy_script.sh

# ✅ BON : Créer une documentation
touch copilot-app/docs/guides/new_guide.md

# ❌ MAUVAIS : Ne pas créer à la racine
# touch new_service.py  # ❌ INTERDIT
```

### 🎯 SI VOUS TRAVAILLEZ SUR L'AGENT OSS

**EMPLACEMENT CORRECT :** `/agent-stack-oss/`

#### 📁 Structure recommandée :
```
agent-stack-oss/
├── src/                    ← Code source principal de l'agent
│   ├── agents/            ← Agents spécialisés
│   ├── tools/             └── Outils de l'agent
│   ├── memory/            └── Gestion de la mémoire
│   └── utils/             └── Fonctions utilitaires
├── training-materials/     ← Matériaux de formation
│   ├── docs/              ← Documentation pédagogique
│   ├── exercises/         └── Exercices pratiques
│   └── examples/          └── Exemples de code
├── tests/                 ← Tests de l'agent
│   ├── unit/             ← Tests unitaires
│   ├── integration/      └── Tests d'intégration
│   └── e2e/              └── Tests end-to-end
└── docs/                  ← Documentation de l'agent
    ├── architecture/     ← Architecture de l'agent
    ├── api/              └── Documentation API
    └── guides/           └── Guides d'utilisation
```

#### 📄 Exemples de création de fichiers :
```bash
# ✅ BON : Créer un nouvel agent
touch agent-stack-oss/src/agents/new_agent.py

# ✅ BON : Créer un exercice de formation
touch agent-stack-oss/training-materials/exercises/new_exercise.md

# ✅ BON : Créer un test
touch agent-stack-oss/tests/unit/test_new_feature.py

# ✅ BON : Créer une documentation
touch agent-stack-oss/docs/guides/new_agent_guide.md

# ❌ MAUVAIS : Ne pas créer à la racine
# touch new_agent.py  # ❌ INTERDIT
```

## 🚫 CE QUI EST INTERDIT

### À LA RACINE DU REPOSITORY (`/analyse-financiere/`)
Ne **JAMAIS** créer de fichiers ici sauf :
- Scripts d'orchestration principaux (`copilot.sh`)
- Fichiers de configuration générale (`.gitignore`, `.env.sample`)
- Documentation principale (`README.md`)

### ❌ INTERDIT ABSOLUMENT :
```bash
# Ces actions sont strictement interdites :
❌ touch analyse-financiere/new_script.py
❌ touch analyse-financiere/config.json
❌ touch analyse-financiere/data.csv
❌ mkdir analyse-financiere/new_folder
❌ touch new_script.py  # Si vous êtes dans la racine
```

## ✅ BONNES PRATIQUES

### 1. Organisation par fonctionnalité
```bash
# Pour une nouvelle fonctionnalité "market-analysis":
# ✅ BON
mkdir -p copilot-app/backend/src/market_analysis
mkdir -p copilot-app/frontend/webapp/src/components/market-analysis
mkdir -p copilot-app/docs/guides/market-analysis

# ❌ MAUVAIS
touch copilot-app/backend/src/market_analysis.py
touch copilot-app/frontend/webapp/src/MarketAnalysis.tsx
```

### 2. Nommage cohérent
```bash
# ✅ BON : Nommage cohérent et descriptif
copilot-app/backend/src/news_aggregator.py
copilot-app/frontend/webapp/src/components/NewsAggregator.tsx
copilot-app/docs/guides/news-aggregation.md

# ❌ MAUVAIS : Nommage incohérent
copilot-app/backend/src/NewsAggregator.py
copilot-app/frontend/webapp/src/news-aggregator.tsx
copilot-app/docs/guides/NewsAggregation.md
```

### 3. Documentation intégrée
```bash
# ✅ BON : Toujours accompagner le code de documentation
touch copilot-app/backend/src/new_module.py
touch copilot-app/docs/guides/new-module-usage.md

# ❌ MAUVAIS : Code sans documentation
touch copilot-app/backend/src/new_module.py
# (pas de documentation)
```

## 🛠️ OUTILS DE VÉRIFICATION

### Script de vérification de l'organisation
```bash
# Vérifier que vous êtes dans le bon dossier
pwd  # Doit afficher /chemin/vers/analyse-financiere

# Vérifier la structure actuelle
ls -la copilot-app/
ls -la agent-stack-oss/

# Vérifier que rien n'a été créé à la racine
ls -la *.py *.sh *.md 2>/dev/null || echo "Aucun fichier à la racine - OK"
```

### Commandes de nettoyage si erreur
```bash
# Si vous avez accidentellement créé des fichiers à la racine :
# 1. Déplacer vers le bon emplacement
mv fichier_mal_place.py copilot-app/backend/src/

# 2. OU supprimer si ce n'est pas utile
rm fichier_inutile.py
```

## 📞 SUPPORT

Si vous avez des doutes sur l'endroit où créer un fichier :
1. Consultez ce guide
2. Vérifiez la structure existante
3. Contactez l'équipe de coordination

**Rappelez-vous : Respectez toujours la séparation des projets et l'organisation par dossiers !** 🎯