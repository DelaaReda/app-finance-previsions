# 🔧 Fix Backend Startup Issues

## ❌ Problème Actuel

Le backend ne peut pas démarrer à cause de :
1. **Venv manquant ou corrompu** : `/Users/venom/Documents/analyse-financiere/copilot-app/backend/.venv` n'existe pas
2. **Dépendances non installées** : `fastapi`, `uvicorn`, `pandas`, etc. ne sont pas disponibles
3. **Import errors** : `ModuleNotFoundError: No module named 'storage.io'` dans `src/api/services/macro_service.py`

## ✅ Solutions

### Option 1 : Utiliser le script officiel (RECOMMANDÉ)

Le script `start.sh` devrait créer le venv et installer les dépendances automatiquement :

```bash
cd /Users/venom/Documents/analyse-financiere
./finance-copilot.sh start
```

**Si le script échoue**, vérifiez que :
- Python 3.9+ est installé
- `python3 -m venv` fonctionne (sinon : `brew install python3` sur macOS)

### Option 2 : Créer le venv manuellement

```bash
cd /Users/venom/Documents/analyse-financiere/copilot-app/backend

# Supprimer l'ancien venv s'il existe
rm -rf .venv

# Créer un nouveau venv
python3 -m venv .venv

# Activer le venv
source .venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Si requirements.txt n'existe pas, installer manuellement :
pip install fastapi uvicorn[standard] python-multipart pydantic pandas requests apscheduler
```

### Option 3 : Installer les dépendances globalement (si venv ne fonctionne pas)

```bash
# Sur macOS avec Homebrew
brew install python3
python3 -m pip install --user fastapi uvicorn[standard] python-multipart pydantic pandas requests apscheduler
```

## 🔍 Vérification

Après installation, vérifiez que tout fonctionne :

```bash
cd /Users/venom/Documents/analyse-financiere/copilot-app/backend
source .venv/bin/activate  # Si venv existe
python3 -c "import fastapi, uvicorn; print('✅ Dependencies OK')"
python3 run_api.py
```

Le backend devrait démarrer sur `http://127.0.0.1:8050`

## 📝 Note sur l'import `storage.io`

Le fichier `src/api/services/macro_service.py` a été corrigé pour gérer les imports avec fallback. Si vous voyez encore l'erreur `ModuleNotFoundError: No module named 'storage.io'`, assurez-vous que :

1. Le fichier `backend/storage/io.py` existe
2. Le fichier `backend/storage/__init__.py` existe
3. Le `PYTHONPATH` inclut le répertoire `backend/`

Le code dans `macro_service.py` devrait maintenant gérer automatiquement ces cas.

## 🚀 Prochaines étapes

Une fois le backend démarré :
1. Vérifiez `http://localhost:8050/api/health`
2. Vérifiez que le frontend peut se connecter via le proxy Vite
3. Testez les endpoints : `/api/forecasts`, `/api/intelligence/snapshot`, etc.

