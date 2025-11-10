# 🔧 Troubleshooting Backend - Guide pour Agents

## 🚨 Problème : Timeouts et erreurs HTTP 500

### Symptômes
- Erreurs "Request timeout after 15000ms" dans la console
- Erreurs HTTP 500 sur `/api/forecasts`, `/api/health`, `/api/macro/series`
- Messages "Backend unavailable" dans l'UI

### Cause principale
**Le backend n'est pas démarré ou ne répond pas sur le port 8050.**

---

## ✅ Solutions

### 1. Vérifier si le backend est démarré

```bash
# Vérifier les processus
ps aux | grep -E "uvicorn|python.*main.py|fastapi" | grep -v grep

# Vérifier le port 8050
curl http://localhost:8050/api/health
```

**Si le backend n'est pas démarré**, vous verrez :
- `curl: (7) Failed to connect to localhost port 8050`
- Aucun processus Python/uvicorn

### 2. Démarrer le backend

**Option A : Script officiel (recommandé)**
```bash
cd /mnt/utm
./finance-copilot.sh start
```

**Option B : Backend seul**
```bash
cd /mnt/utm/copilot-app/backend
python run_api.py
```

**Option C : Uvicorn directement**
```bash
cd /mnt/utm/copilot-app/backend
uvicorn api.main:app --host 0.0.0.0 --port 8050 --reload
```

### 3. Vérifier les logs backend

```bash
# Logs du backend
tail -f copilot-app/backend/api.log

# Ou si lancé avec uvicorn directement
# Les logs apparaissent dans le terminal
```

### 4. Vérifier les erreurs Python

Si le backend ne démarre pas, vérifier :
- **Imports manquants** : `pip install -r requirements.txt`
- **Chemins incorrects** : Vérifier que `PYTHONPATH` est correct
- **Port déjà utilisé** : `lsof -i :8050` (Linux/Mac) ou `netstat -ano | findstr :8050` (Windows)

---

## 🔍 Diagnostic des erreurs spécifiques

### Erreur : "Request timeout after 15000ms"

**Causes possibles** :
1. Backend non démarré (le plus fréquent)
2. Backend trop lent (endpoint prend >15s)
3. Problème réseau/proxy

**Solutions** :
- ✅ Timeouts augmentés automatiquement pour endpoints lents :
  - `/api/macro/series` : 30s (FRED peut être lent)
  - `/api/forecasts` : 25s
  - `/api/brief/*` : 25s
  - `/api/backtests` : 60s
- ✅ Vérifier que le backend répond : `curl http://localhost:8050/api/health`
- ✅ Vérifier les logs backend pour voir si l'endpoint traite la requête

### Erreur : "HTTP 500 Internal Server Error"

**Causes possibles** :
1. Exception Python dans le backend
2. Fichier de données manquant ou corrompu
3. Problème d'import de module

**Solutions** :
- ✅ Vérifier les logs backend : `tail -f copilot-app/backend/api.log`
- ✅ Vérifier que les fichiers de données existent :
  ```bash
  ls -la copilot-app/backend/data/*.json
  ```
- ✅ Vérifier les imports Python :
  ```bash
  cd copilot-app/backend
  python -c "from storage.io import load_json; print('OK')"
  ```

### Erreur : "Backend unavailable"

**Cause** : Le backend n'est pas accessible (pas démarré ou port bloqué)

**Solution** :
- ✅ Démarrer le backend (voir section 2)
- ✅ Vérifier que le port 8050 n'est pas bloqué par un firewall
- ✅ Vérifier que le proxy Vite fonctionne : `curl http://localhost:5173/api/health`

---

## 📊 Vérification rapide

### Checklist avant de signaler un problème

- [ ] Backend démarré : `curl http://localhost:8050/api/health` retourne `{"ok": true, ...}`
- [ ] Frontend accessible : http://localhost:5173 charge
- [ ] Proxy Vite fonctionne : `curl http://localhost:5173/api/health` retourne la même chose
- [ ] Logs backend consultés : Pas d'erreurs Python dans `api.log`
- [ ] Fichiers de données présents : `ls copilot-app/backend/data/*.json` montre des fichiers

---

## 🛠️ Commandes utiles

```bash
# Démarrer tout (backend + frontend)
./finance-copilot.sh start

# Démarrer backend seul
./finance-copilot.sh start-backend

# Arrêter tout
./finance-copilot.sh stop

# Vérifier l'état
./finance-copilot.sh status

# Vérifier backend directement
curl http://localhost:8050/api/health
curl http://localhost:8050/api/forecasts?limit=5
curl http://localhost:8050/api/macro/series?ids=CPIAUCSL

# Vérifier via proxy frontend
curl http://localhost:5173/api/health
curl http://localhost:5173/api/forecasts?limit=5
```

---

## 📝 Notes pour les agents

- **Toujours vérifier que le backend est démarré** avant de signaler des erreurs
- **Consulter les logs backend** (`api.log`) pour voir les vraies erreurs Python
- **Les timeouts sont maintenant adaptatifs** : plus longs pour endpoints lents
- **Les messages d'erreur sont améliorés** : ils indiquent clairement si le backend n'est pas disponible

---

## 🔗 Fichiers modifiés pour corriger les timeouts

- `copilot-app/frontend/webapp/src/api/client.ts` : Timeouts adaptatifs ajoutés
- `copilot-app/frontend/webapp/src/components/widgets/ForecastsProBoard.tsx` : Messages d'erreur améliorés

