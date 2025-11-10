# 🔍 Diagnostic Backend

## Problème
Le backend n'est pas accessible sur le port 8050.

## Vérifications à Faire

### 1. Vérifier que le backend est démarré
```bash
ps aux | grep uvicorn | grep -v grep
```

### 2. Vérifier le port
```bash
lsof -i :8050
# ou
netstat -tuln | grep 8050
```

### 3. Vérifier les logs
```bash
tail -f copilot-app/backend/api.log
```

### 4. Démarrer le backend
```bash
./finance-copilot.sh start
```

### 5. Vérifier les erreurs de démarrage
Si le backend ne démarre pas, vérifier:
- Erreurs dans api.log
- Problèmes d'import
- Problèmes de port déjà utilisé

## Solutions

### Si le port est déjà utilisé
```bash
lsof -i :8050
kill -9 <PID>
./finance-copilot.sh start
```

### Si erreurs d'import
Vérifier que l'environnement virtuel est activé:
```bash
cd copilot-app/backend
source .venv/bin/activate  # ou .venv/Scripts/activate sur Windows
python3 -c "import fastapi; print('OK')"
```

### Si le backend démarre mais ne répond pas
Vérifier les logs pour voir les erreurs de routes ou de middleware.
