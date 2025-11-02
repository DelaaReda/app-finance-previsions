# 📁 STRUCTURE DU PROJET FINANCE COPILOT

## 🎯 Organisation Principale

```
analyse-financiere/
├── copilot-app/                    ← Application Finance Copilot principale
│   ├── backend/                    ← Backend Python (API FastAPI)
│   │   ├── api/                    ← API principale
│   │   ├── src/                    ← Source code backend
│   │   ├── run_api.py             ← Point d'entrée backend
│   │   ├── api.log               ← Logs backend
│   │   └── .venv/                ← Environnement Python virtuel
│   ├── frontend/                 ← Frontend React
│   │   └── webapp/               ← Application web React/Vite
│   │       ├── src/              ← Source code frontend
│   │       ├── frontend.log     ← Logs frontend
│   │       └── vite.config.ts    ← Configuration Vite
│   ├── scripts/                  ← Scripts de gestion
│   │   ├── start.sh             ← Démarrage de l'application
│   │   ├── stop.sh              ← Arrêt de l'application
│   │   └── test_system.sh       ← Test du système
│   └── docs/                     ← Documentation
│       └── README_SCRIPTS.md    ← Guide d'utilisation
├── agent-stack-oss/              ← Agent OSS (projet séparé)
│   ├── src/
│   ├── training-materials/
│   └── ...
└── copilot.sh                    ← Script principal à la racine
```

## 🚀 Démarrage Rapide

### 1. Démarrer l'application
```bash
./copilot.sh start
```

### 2. Vérifier l'état
```bash
./copilot.sh status
```

### 3. Arrêter l'application
```bash
./copilot.sh stop
```

## 🌐 URLs Disponibles

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8050
- **Documentation API**: http://localhost:8050/docs

## 📂 Structure Détaillée

### `copilot-app/backend/`
Contient tout le code backend Python :
- API FastAPI dans `api/main.py`
- Services métier dans `src/`
- Point d'entrée `run_api.py`
- Environnement virtuel `.venv/`

### `copilot-app/frontend/webapp/`
Contient l'application React/Vite :
- Code source dans `src/`
- Configuration Vite dans `vite.config.ts`
- Dépendances Node dans `package.json`

### `copilot-app/scripts/`
Scripts de gestion de l'application :
- `start.sh` : Démarrage complet
- `stop.sh` : Arrêt sécurisé
- `test_system.sh` : Diagnostics

## ⚙️ Commandes Utiles

### Gestion de l'application
```bash
# Démarrer tous les services
./copilot.sh start

# Arrêter tous les services
./copilot.sh stop

# Redémarrer tous les services
./copilot.sh restart

# Vérifier l'état des services
./copilot.sh status

# Tester le système
./copilot.sh test
```

### Accès direct aux services
```bash
# Démarrer uniquement le backend
cd copilot-app/backend && python run_api.py

# Démarrer uniquement le frontend
cd copilot-app/frontend/webapp && npm run dev
```

## 🧪 Tests

### Test des endpoints backend
```bash
# Test de santé
curl http://localhost:8050/api/health

# Test de génération de brief
curl http://localhost:8050/api/brief/daily

# Test du tableau de bord
curl http://localhost:8050/api/dashboard/kpis
```

### Test du frontend
```bash
# Accès à la page principale
curl http://localhost:5173/
```

## 🛠️ Dépannage

### Problèmes fréquents

1. **Ports occupés**:
   ```bash
   # Libérer les ports
   ./copilot.sh stop
   lsof -i :8050 | xargs kill -9
   lsof -i :5173 | xargs kill -9
   ```

2. **Dépendances manquantes**:
   ```bash
   # Backend (Python)
   cd copilot-app/backend
   source .venv/bin/activate
   pip install uvicorn fastapi
   
   # Frontend (Node)
   cd copilot-app/frontend/webapp
   npm install
   ```

3. **Permissions**:
   ```bash
   chmod +x copilot.sh
   chmod +x copilot-app/scripts/*.sh
   ```

## 📞 Support

Pour toute question ou problème :
1. Exécutez `./copilot.sh status` pour diagnostiquer
2. Vérifiez les logs dans `copilot-app/backend/api.log` et `copilot-app/frontend/webapp/frontend.log`
3. Contactez l'équipe de développement avec les logs d'erreur