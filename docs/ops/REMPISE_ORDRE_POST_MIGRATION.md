# Remise en ordre post-migration – Plan d'action

**Date:** 2026-02-28  
**Contexte:** Plusieurs agents ont travaillé après la grosse migration Feb 27–28. Audit complet effectué pour identifier ce qui doit être corrigé.

---

## ✅ Ce qui fonctionne déjà

| Élément | Status |
|--------|--------|
| **Backend** | ✅ UP (http://localhost:8050) |
| **Frontend** | ✅ UP (http://localhost:5173) |
| **Health endpoint** | ✅ `last_updates` rempli (forecasts, news, brief_weekly) |
| **Workspace layout** | ✅ 21/21 checks pass (validate_agent_workspace_layout.sh) |
| **Parallel plumbing** | ✅ 18/18 checks pass |
| **Jobs legacy** | ✅ Présents dans `apps/api/src/platform/legacy/jobs/` |
| **Architecture** | ✅ `apps/api`, `apps/web`, `platform`, `packages` en place |

---

## ✅ Corrections appliquées (2026-02-28)

| Correction | Status |
|------------|--------|
| backend_regression_gate.sh (ROOT + pytest) | ✅ Fait |
| Fichier parasite supprimé | ✅ Fait |
| chmod +x regression gate | ✅ Fait |
| copilot-app archivé | ✅ Fait |
| api.log → runtime/ | ✅ Fait |
| finance-app/openclaw-gates créé | ✅ Fait |
| pytest.ini ajouté | ✅ Fait |
| MIGRATION_SUMMARY mis à jour | ✅ Fait |

---

## 🔴 Corrections requises (priorité) – historiques

**Problème:** Le script calcule `ROOT` avec `SCRIPT_DIR/../..` (2 niveaux) au lieu de `SCRIPT_DIR/..` (1 niveau). Résultat : `BACKEND_DIR=/home/venom/shared/apps/api/src` (inexistant).

**Solution:**
```bash
# Dans scripts/backend_regression_gate.sh, ligne 11 :
# Remplacer :
  ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
# Par :
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
```

---

### 2. Regression gate – découverte des tests

**Problème:** Le gate lance `pytest tests` mais :
- `apps/api/src/tests` → symlink vers `../tests` (apps/api/tests)
- `apps/api/tests/` ne contient que `__pycache__/` (vide)
- Les vrais tests sont dans `apps/api/src/domains/*/tests/`

**Solution:** Adapter la commande pytest pour découvrir les tests :
```bash
# Remplacer : PYTHONPATH=. "$PYTEST_BIN" -q tests
# Par : PYTHONPATH=. "$PYTEST_BIN" -q domains/
```

Ou créer un `pytest.ini` / `pyproject.toml` dans `apps/api/src/` avec :
```ini
[tool.pytest.ini_options]
testpaths = ["domains"]
```

---

### 3. Fichier parasite à la racine

**Problème:** Fichier créé par erreur (typo shell) :
```
./%ln | head -n 80'
```

**Solution:**
```bash
rm -f "/home/venom/analyse-financiere/%ln | head -n 80'"
```

---

### 4. Répertoires résiduels `copilot-app/` et `finance-app/`

**Problème:**
- `copilot-app/backend/` : contient `data/` et `.pytest_cache` (résidu migration)
- `finance-app/` : contient `orchestrator-runs/`, `sdk_sessions.json` – **utilisé par docs/crons**

**Action:**
- **copilot-app/** : déplacer vers `archive/structure-migrations/copilot-app-residual-20260228/` (archive propre)
- **finance-app/** : **ne pas supprimer** – référencé par `docs/product/planning/tasks.md` et cron runner pour `orchestrator-runs/` et `openclaw-gates/`. Vérifier si `finance-app/openclaw-gates/` existe ; si non, le créer ou mettre à jour les références vers `evidence/` ou `logs/`.

---

### 5. api.log dans `apps/api/src/`

**Problème:** Le script `copilot.sh` écrit `api.log` dans `$BACKEND_DIR` (apps/api/src/). Le README indique `apps/api/runtime/api.log`.

**Solution:** Modifier `apps/api/runtime/copilot.sh` ligne 268 :
```bash
# Remplacer : nohup "$PY" run_api.py > api.log 2>&1 &
# Par : nohup "$PY" run_api.py > "$SCRIPT_DIR/api.log" 2>&1 &
# (SCRIPT_DIR = apps/api/runtime, donc api.log dans runtime/)
```

---

### 6. `.venv` incomplet

**Problème:** Le `.venv` à la racine n'a que `lib/` (pas de `bin/`). Le backend utilise `/usr/bin/python3` système. Les scripts migration mentionnent `.venv/bin/python`.

**Action:** Option A) Recréer un venv propre :
```bash
cd /home/venom/analyse-financiere
python3 -m venv .venv
.venv/bin/pip install -r apps/api/src/requirements.txt  # si existe
.venv/bin/pip install pytest fastapi uvicorn
```
Option B) Documenter que le projet tourne avec Python système et mettre à jour les scripts pour utiliser `python3` si `.venv` absent.

---

### 7. Permission `backend_regression_gate.sh`

**Problème:** `Permission denied` à l'exécution directe.

**Solution:**
```bash
chmod +x scripts/backend_regression_gate.sh
```

---

## ⚠️ À mettre à jour (documentation)

### MIGRATION_SUMMARY.md
- Cocher **Health endpoint OK** et **Jobs réactivés** (déjà fonctionnels)
- RAG fake : pas de fichier `news.jsonl` trouvé → considérer résolu ou documenter

### Références obsolètes dans la doc
- Remplacer `copilot-app/backend/` par `apps/api/src/` dans les docs
- Remplacer `copilot-app/frontend/` par `apps/web/src/`
- `finance-app/openclaw-gates/` : vérifier existence, créer si nécessaire ou rediriger vers `evidence/`

---

## 📋 Checklist d'exécution

```bash
# 1. Nettoyage immédiat
rm -f "/home/venom/analyse-financiere/%ln | head -n 80'"
chmod +x scripts/backend_regression_gate.sh

# 2. Corriger backend_regression_gate.sh (ROOT + pytest path)
# 3. Corriger copilot.sh (api.log vers runtime)
# 4. Archiver copilot-app résiduel
mv copilot-app archive/structure-migrations/copilot-app-residual-20260228

# 5. Vérifier finance-app/openclaw-gates
mkdir -p finance-app/openclaw-gates
# ou mettre à jour les références dans tasks.md

# 6. Relancer gate après corrections
bash scripts/backend_regression_gate.sh --no-live

# 7. Mettre à jour MIGRATION_SUMMARY.md
```

---

## 📊 Résumé

| Catégorie | Nb items | Priorité |
|-----------|----------|----------|
| Scripts cassés | 2 (regression_gate, copilot) | P0 |
| Nettoyage fichiers | 2 (parasite, copilot-app) | P1 |
| Documentation | 2 (MIGRATION_SUMMARY, chemins) | P2 |
| Venv / env | 1 (optionnel) | P3 |

---

*Document généré par audit – 2026-02-28*
