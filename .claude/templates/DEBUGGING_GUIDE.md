# Guide de Debugging Rapide

## 🚨 Erreurs Courantes et Solutions Immédiates

### Frontend: Build Errors

#### Erreur: "Multiple exports with the same name"
```
ERROR: Multiple exports with the same name "functionName"
```

**Cause**: Fonction exportée 2 fois dans même fichier

**Solution immédiate**:
```bash
# 1. Chercher le nom de la fonction
grep -n "export.*functionName" file.ts

# 2. Supprimer la duplication (garder 1 seule)
# 3. Rebuild
pnpm build
```

#### Erreur: "Cannot find module '@/...'"
```
ERROR: Cannot find module '@/components/Something'
```

**Cause**: Import path incorrect ou fichier n'existe pas

**Solution immédiate**:
```bash
# 1. Vérifier le fichier existe
ls copilot-app/frontend/webapp/src/components/Something.tsx

# 2. Si n'existe pas, créer OU corriger l'import
# 3. Vérifier tsconfig.json a le path alias "@"
```

#### Erreur: "Property 'X' does not exist"
```
ERROR: Property 'items' does not exist on type 'undefined'
```

**Cause**: Accès à propriété sans safe check

**Solution immédiate**:
```typescript
// ❌ AVANT
const items = data.items

// ✅ APRÈS
import { safeArray } from '@/lib/safe'
const items = safeArray(data?.items)
```

### Backend: Import Errors

#### Erreur: "ModuleNotFoundError: No module named 'X'"
```
ModuleNotFoundError: No module named 'backend.services.X'
```

**Cause**: Import path incorrect OU module n'existe pas

**Solution immédiate**:
```bash
# 1. Vérifier le fichier existe
find . -name "X.py"

# 2. Si existe, corriger l'import path
# Exemple: from backend.services.X -> from services.X

# 3. Vérifier sys.path setup dans le fichier
# Doit avoir:
import sys
from pathlib import Path
backend_root = Path(__file__).resolve().parents[N]  # N = combien de parents
sys.path.insert(0, str(backend_root))
```

#### Erreur: "cannot import name 'function_name'"
```
ImportError: cannot import name 'run_something'
```

**Cause**: Nom de fonction incorrect OU fonction pas exportée

**Solution immédiate**:
```bash
# 1. Vérifier le nom exact dans le fichier
grep "def " copilot-app/backend/path/to/file.py

# 2. Corriger l'import avec le bon nom
# 3. Redémarrer le backend
```

### Backend: Endpoint 404

#### Erreur: "404: Not Found" sur POST request
```
POST /api/something 404: Not Found
```

**Cause**: Endpoint attend Query params mais frontend envoie JSON body (ou inverse)

**Solution immédiate**:
```python
# ❌ MAUVAIS: Query params
@app.post("/api/something")
async def something(param: str = Query(...)):
    ...

# ✅ BON: JSON body
from pydantic import BaseModel

class SomethingRequest(BaseModel):
    param: str

@app.post("/api/something")
async def something(request: SomethingRequest):
    ...
```

### Backend: Data vide

#### Erreur: Endpoint retourne `{"rows": []}`
```json
{"ok": true, "data": {"rows": [], "count": 0}}
```

**Cause**: Fichier JSON n'existe pas OU service ne le lit pas

**Solution immédiate**:
```bash
# 1. Vérifier le fichier existe
ls copilot-app/backend/data/forecasts.json

# 2. Vérifier qu'il contient des données
head -20 copilot-app/backend/data/forecasts.json

# 3. Vérifier l'endpoint utilise load_json()
grep "load_json" copilot-app/backend/src/api/main.py

# 4. Si pas load_json, ajouter:
from storage.io import load_json
data = load_json("forecasts")  # sans .json extension
```

### Git: Commit Hook Failed

#### Erreur: "Missing trailer: Task: FC-XXXX"
```
❌ Missing trailer: Task: FC-XXXX
```

**Cause**: Trailer manquant ou format incorrect

**Solution immédiate**:
```bash
# Vérifier que commit message a TOUS ces trailers:
Task: FC-XXX-YYY
Agent: @YOUR-NAME
Domain: Something
Proofs: proofs/FC-XXX-YYY/YOUR-NAME/
TimeSpent: XXmin

# Note: DOIT être sur lignes séparées, avec exact format
```

#### Erreur: "Missing trailer: Proofs: path"
```
❌ Missing trailer: Proofs: path
```

**Cause**: Proof trailer existe mais pas de dossier/fichier

**Solution immédiate**:
```bash
# 1. Créer le dossier proof
mkdir -p proofs/FC-XXX-YYY/YOUR-NAME/

# 2. Créer un fichier proof dedans
echo "✅ Task done" > proofs/FC-XXX-YYY/YOUR-NAME/PROOF.md

# 3. Add et re-commit
git add proofs/
git commit --amend
```

## 🔍 Techniques de Debug Rapides

### Frontend

#### Vérifier si component crash
```bash
# 1. Ouvrir browser console (F12)
# 2. Chercher erreur rouge
# 3. Noter ligne exacte
# 4. Aller à la ligne, ajouter safe check
```

#### Vérifier API call
```bash
# 1. Browser DevTools -> Network tab
# 2. Refresh page
# 3. Chercher l'API call
# 4. Vérifier Status (200 OK, 404, 500)
# 5. Vérifier Response (JSON valide?)
```

#### Test build local
```bash
cd copilot-app/frontend/webapp
pnpm build
# Si erreur -> lire première erreur (pas toutes)
# Corriger cette erreur
# Re-run
```

### Backend

#### Vérifier endpoint fonctionne
```bash
# GET request
curl http://localhost:8050/api/forecasts | jq '.'

# POST request with JSON
curl -X POST http://localhost:8050/api/something \
  -H 'Content-Type: application/json' \
  -d '{"param": "value"}' | jq '.'

# Vérifier:
# - Status 200 OK (pas 404, 500)
# - JSON valide
# - Data présente
```

#### Vérifier fichier data existe
```bash
ls -lh copilot-app/backend/data/

# Vérifier size > 0
# Si 0 bytes -> fichier vide, problème
```

#### Check backend logs
```bash
# Les logs s'affichent dans le terminal où backend run
# Chercher "ERROR" ou "Exception"
# Lire stacktrace du bas vers le haut
```

## ⚡ Checklist Debug 5 Minutes

Quand quelque chose ne marche pas:

### Frontend issue
- [ ] Browser console a des erreurs? -> Lire première erreur
- [ ] Network tab montre 404/500? -> Vérifier endpoint existe backend
- [ ] Component blanc? -> Ajouter safe checks (`safeArray`, `hasItems`)
- [ ] `pnpm build` passe? -> Fix build errors avant tout

### Backend issue
- [ ] Endpoint existe dans `main.py`? -> `grep "@app" copilot-app/backend/src/api/main.py`
- [ ] Fichier data existe? -> `ls copilot-app/backend/data/`
- [ ] Import paths corrects? -> Run file standalone: `python3 path/to/file.py`
- [ ] Curl retourne 200? -> Test manuel

### Git issue
- [ ] Tous les trailers présents? -> Copy/paste template
- [ ] Proof folder existe? -> `ls proofs/FC-XXX/`
- [ ] Message format correct? -> Check exemple

## 🎯 Règle d'Or

**Si bloqué > 10 minutes -> STOP et demander dans COMMS**

Template message:
```markdown
[UTC YYYY-MM-DD HH:MM] [BLOCKER] MSG: MSG-YYYYMMDD-HHMM-YOUR-NAME
From: @YOUR-NAME  →  To: @ALL
Task: FC-XXX-YYY
Subject: Bloqué sur [issue brief]
Message:
- Context: Working on X
- Problem: Y ne marche pas
- Tried: A, B, C
- Error: [exact error message]
- Need: Guidance on how to fix
Links:
- File: path/to/file.py:123
```

**NE PAS** perdre 1h à essayer des choses random. Demander aide rapidement.
