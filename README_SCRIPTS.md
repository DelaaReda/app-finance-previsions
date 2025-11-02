# 🚀 Finance Copilot - Scripts de Gestion

Ce répertoire contient des scripts utilitaires pour gérer facilement l'application Finance Copilot.

## 📋 Scripts Disponibles

### `start.sh` - Démarrage complet
Démarre à la fois le backend (API) et le frontend (interface utilisateur).

```bash
./start.sh
```

**URLs après démarrage:**
- Frontend: http://localhost:5173
- Backend: http://localhost:8050
- Documentation API: http://localhost:8050/docs

### `stop.sh` - Arrêt complet
Arrête tous les services et libère les ports.

```bash
./stop.sh
```

### `test_system.sh` - Test du système
Vérifie que tous les services fonctionnent correctement.

```bash
./test_system.sh
```

## ▶️ Démarrage Rapide

1. **Démarrer l'application:**
   ```bash
   ./start.sh
   ```

2. **Accéder à l'application:**
   Ouvrez votre navigateur à http://localhost:5173

3. **Vérifier le fonctionnement:**
   ```bash
   ./test_system.sh
   ```

4. **Arrêter l'application:**
   ```bash
   ./stop.sh
   ```

## 🛠️ Commandes Avancées

### Redémarrer tous les services:
```bash
./start.sh restart
```

### Vérifier l'état des services:
```bash
./start.sh status
```

### Afficher l'aide:
```bash
./start.sh help
```

## 📊 URLs et Ports

| Service | URL | Port |
|---------|-----|------|
| Frontend (Interface) | http://localhost:5173 | 5173 |
| Backend (API) | http://localhost:8050 | 8050 |
| Documentation API | http://localhost:8050/docs | 5173 |

## 📁 Structure des Logs

- **Backend:** `api.log` (dans le répertoire racine)
- **Frontend:** `webapp/frontend.log`

## 🔧 Dépannage

### Si les services ne démarrent pas:
1. Exécutez `./stop.sh` pour tuer tous les processus
2. Vérifiez que les ports 8050 et 5173 sont libres
3. Réessayez avec `./start.sh`

### Si vous voyez des erreurs de dépendances:
```bash
# Backend
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd webapp
npm install
```

### Pour voir les logs en temps réel:
```bash
# Backend
tail -f api.log

# Frontend
tail -f webapp/frontend.log
```

## 🎯 Points Importants

- Le backend doit être démarré avant le frontend pour que le proxy fonctionne correctement
- Le premier démarrage peut prendre quelques minutes car les dépendances sont vérifiées
- Les données sont générées automatiquement au premier accès si nécessaire
- Le système crée des fichiers de cache dans le répertoire `data/`

## 🆘 Support

Si vous rencontrez des problèmes persistants:

1. Exécutez `./test_system.sh` pour diagnostiquer
2. Vérifiez les logs (`tail -f api.log` et `tail -f webapp/frontend.log`)
3. Assurez-vous que toutes les dépendances sont installées
4. Contactez l'équipe de développement avec les logs d'erreur