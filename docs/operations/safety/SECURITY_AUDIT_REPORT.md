# 🔒 Audit de Sécurité - Projet analyse-financiere

**Date:** 2026-02-23  
**Statut:** ✅ Audit complet  
**Risque Global:** 🟡 MOYEN (actions correctives requises)

---

## 📋 RÉSUMÉ EXÉCUTIF

| Catégorie | État | Risque | Actions Requises |
|-----------|------|--------|------------------|
| Dépendances Python | ⚠️ | Moyen | 3 |
| Scripts shell | ✅ | Faible | 1 |
| Secrets/Env | 🔴 | Élevé | 2 |
| Hooks Git | ✅ | Faible | 0 |
| Permissions | ✅ | Faible | 0 |
| Composants externes | ⚠️ | Moyen | 2 |

---

## 1. 🔍 DÉPENDANCES PYTHON

### 1.1 Dépendances principales (requirements.txt)

```
fastapi>=0.104.1          # ✅ PyPI officiel - OK
uvicorn[standard]>=0.24.0 # ✅ PyPI officiel - OK
pandas>=2.0.0             # ✅ PyPI officiel - OK
duckdb>=1.4.3             # ✅ PyPI officiel - OK
yfinance>=0.2.44          # ✅ PyPI officiel - OK
feedparser>=6.0.10        # ✅ PyPI officiel - OK
apscheduler>=3.10.0       # ✅ PyPI officiel - OK
sentry-sdk[fastapi]>=2.0.0 # ✅ PyPI officiel - OK
massive>=2.0.3            # ⚠️ Vérifier provenance
pytest>=9.0.2             # ✅ PyPI officiel - OK (dev)
```

### 1.2 Packages installés (extraits critiques)

```
g4f==6.6.6                # ⚠️ Provider LLM gratuit - source à valider
autogen==0.10.2           # ✅ Microsoft - OK
playwright==1.57.0        # ✅ Microsoft - OK
curl_cffi==0.13.0         # ⚠️ Curl impersonation - usage à auditer
```

### 1.3 Risques identifiés

| Package | Risque | Recommandation |
|---------|--------|----------------|
| `g4f` | Provider LLM non-officiel, contournement potentiel de restrictions | Remplacer par OpenRouter officiel ou DeepInfra direct |
| `curl_cffi` | Curl impersonation (peut être utilisé pour bypass) | Restreindre usage aux endpoints validés |
| `massive` | Package peu connu | Vérifier GitHub officiel et mainteneur |

---

## 2. 🛡️ SCRIPTS SHELL

### 2.1 Scripts audités

| Script | Permissions | Risque | Statut |
|--------|-------------|--------|--------|
| `finance-copilot.sh` | 755 | ✅ Faible | OK - Wrapper simple |
| `copilot-app/copilot.sh` | 755 | ✅ Faible | OK - Bien structuré |
| `scripts/smoke.sh` | 755 | ✅ Faible | OK - Test santé |
| `scripts/fetch_prices_yahoo.sh` | 755 | ⚠️ Moyen | OK - Cookies requis |
| `scripts/fetch_prices_stooq.sh` | 755 | ✅ Faible | OK |
| `scripts/monitor_qwen_10h.sh` | 755 | ✅ Faible | OK - Monitoring |

### 2.2 Points positifs
- ✅ Pas de `curl | bash` ou téléchargement/exécution directe
- ✅ Pas de `pip install` ou `npm install` dans les scripts runtime
- ✅ Utilisation de `set -euo pipefail` pour la sécurité
- ✅ Validation des chemins avec `readlink -f`

### 2.3 Recommandation
- [ ] Ajouter validation SHA256 des scripts dans `.git/hooks`

---

## 3. 🔑 SECRETS ET ENVIRONNEMENT

### 3.1 Fichier .env - ⚠️ RISQUE ÉLEVÉ

**Problèmes critiques:**

```bash
# ❌ Clés API exposées en clair dans .env
FRED_API_KEY=<REDACTED>
OPEN_ROUTER_API_KEY=<REDACTED>
OPEN_ROUTER_API_KEY_2=<REDACTED>
CODESTRAL_API_KEY=<REDACTED>
GROK_API_KEY=<REDACTED>
SENTRY_AUTH_TOKEN=<REDACTED>

# ❌ Clé FRED exposée
FRED_API_KEY=<REDACTED>

# ⚠️ Secret Key non sécurisée
SECRET_KEY=your-secret-key-here-change-in-production
```

### 3.2 Actions requises (URGENT)

1. **[ ] Révoquer et régénérer TOUTES les clés API exposées**
2. **[ ] Utiliser un gestionnaire de secrets (1Password, Vault, AWS Secrets Manager)**
3. **[ ] Ajouter `.env` à `.gitignore` (déjà fait ✅)**
4. **[] Créer `.env.example` avec valeurs factices**

---

## 4. 🪝 HOOKS GIT

### 4.1 Hooks audités

| Hook | Statut | Protection |
|------|--------|------------|
| `pre-commit` | ✅ Actif | Bloque WIP/TODO/FIXME, legacy, syntax Python/Shell |
| `pre-push` | ✅ Actif | Bloque push sur main/master, vérifie santé backend |
| `commit-msg` | ✅ Présent | Format des messages |

### 4.2 Qualité des guards

```bash
# ✅ Points positifs
- BYPASS_GUARDS=1 requis pour contourner (opt-in explicite)
- Validation syntaxe Python (`py_compile`)
- Validation syntaxe Shell (`bash -n`)
- Protection zone legacy
- Health check backend avant push
```

---

## 5. 🔐 PERMISSIONS FICHIERS

### 5.1 État des permissions

```
-rwxr-xr-x  finance-copilot.sh          # ✅ OK (755)
-rwxr-xr-x  copilot-app/copilot.sh      # ✅ OK (755)
-rwxr-xr-x  scripts/*.sh                # ✅ OK (755)
-rw-r--r--  .env                        # ✅ OK (644 - lisible owner seulement)
-rw-r--r--  mydatabase.db               # ✅ OK (644)
```

### 5.2 Recommandation
- [ ] Changer `.env` en `600` (lecture/écriture owner uniquement)
  ```bash
  chmod 600 copilot-app/backend/.env
  ```

---

## 6. 🧩 COMPOSANTS EXTERNES

### 6.1 Allowlist existante (`SECURITY_ALLOWLIST.md`)

✅ Le projet dispose d'une allowlist documentée

### 6.2 Sources de données

| Source | Type | Statut |
|--------|------|--------|
| Yahoo Finance | API publique | ✅ Autorisée |
| FRED | API gouvernementale | ✅ Autorisée |
| OpenRouter | LLM API | ⚠️ Clé requise |
| G4F | LLM gratuit | ⚠️ À valider |

### 6.3 Web scraping (`web_navigator.py`)

```python
# ✅ Domaines de confiance whitelistés
TRUSTED_FINANCE = (
    "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
    "sec.gov", "nasdaq.com", "marketwatch.com",
)

# ✅ Domaines bloqués
HARD_BLOCK = ("github.com", "stackoverflow.com", "stackexchange.com")
```

---

## 7. ⚠️ CODE SENSIBLE

### 7.1 Usage de `pickle`

**Fichier:** `copilot-app/backend/src/utils/file_loader.py`

```python
# ⚠️ Risque: pickle.load() peut exécuter du code arbitraire
def load_pickle(filename: str, base_path: Optional[str] = None):
    with open(filepath, 'rb') as f:
        return pickle.load(f)  # ❌ Non sécurisé
```

**Recommandation:**
- [ ] Remplacer par `joblib` ou `json`/`parquet` pour les données
- [ ] Si pickle requis, utiliser `PickleLoader` avec classes restreintes
- [ ] Valider hash des fichiers pickle avant chargement

### 7.2 Usage de `subprocess`

**Fichiers:** `tools/make.py`, `tools/git_patcher.py`

```python
# ✅ Usage correct (pas de shell=True, pas d'interpolation utilisateur)
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
```

**Statut:** ✅ Acceptable (commandes internes, pas d'input utilisateur)

### 7.3 Usage de `exec_module`

**Fichier:** `storage/__init__.py`

```python
# ⚠️ Chargement dynamique de module
spec.loader.exec_module(_mod)
```

**Recommandation:**
- [ ] Documenter pourquoi ce chargement dynamique est requis
- [ ] Valider le chemin avant chargement

---

## 8. 📊 SCORE DE SÉCURITÉ

| Catégorie | Score | Commentaire |
|-----------|-------|-------------|
| Dépendances | 6/10 | g4f et curl_cffi à auditer |
| Secrets | 2/10 | ⚠️ Clés exposées - CRITIQUE |
| Scripts | 8/10 | Bien structurés |
| Hooks Git | 9/10 | Excellente couverture |
| Permissions | 7/10 | .env trop permissif |
| Code sensible | 5/10 | pickle non sécurisé |

**Score Global: 6.2/10** - 🟡 **Risque Moyen**

---

## 9. 🎯 PLAN D'ACTION PRIORITAIRE

### 🔴 CRITIQUE (24-48h)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 1 | **Révoquer et régénérer toutes les clés API** | 🔴 Élevé | 🟢 Faible |
| 2 | **Changer permissions .env en 600** | 🟡 Moyen | 🟢 Faible |
| 3 | **Créer .env.example avec valeurs factices** | 🟡 Moyen | 🟢 Faible |

### 🟡 HAUT (1 semaine)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 4 | Remplacer `g4f` par providers officiels | 🟡 Moyen | 🟡 Moyen |
| 5 | Sécuriser `load_pickle()` ou migrer vers joblib | 🟡 Moyen | 🟡 Moyen |
| 6 | Ajouter validation SHA256 des scripts | 🟢 Faible | 🟡 Moyen |
| 7 | Documenter usage `exec_module` | 🟢 Faible | 🟢 Faible |

### 🟢 MOYEN (1 mois)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 8 | Implémenter gestionnaire de secrets | 🟡 Moyen | 🔴 Élevé |
| 9 | Audit complet des dépendances transitives | 🟡 Moyen | 🟡 Moyen |
| 10 | Mettre en place SAST (Static Analysis) | 🟡 Moyen | 🟡 Moyen |

---

## 10. 🔄 PROCÉDURE DE ROLLBACK

### 10.1 Rollback des dépendances

```bash
# Sauvegarder l'état actuel
pip freeze > requirements.current.txt

# Revenir à la version précédente
git checkout HEAD~1 -- copilot-app/backend/requirements.txt
pip install -r copilot-app/backend/requirements.txt
```

### 10.2 Rollback des scripts

```bash
# Restaurer les scripts depuis le dernier commit sûr
git checkout <commit-sûr> -- finance-copilot.sh copilot-app/copilot.sh scripts/
chmod +x finance-copilot.sh copilot-app/copilot.sh scripts/*.sh
```

### 10.3 Rollback des clés API

```bash
# 1. Révoquer les clés actuelles via les portails respectifs:
#    - OpenRouter: https://openrouter.ai/keys
#    - FRED: https://fred.stlouisfed.org/docs/api/api_key.html
#    - Sentry: https://sentry.io/settings/auth-tokens/

# 2. Restaurer .env depuis backup
git checkout <commit-sûr> -- copilot-app/backend/.env

# 3. Régénérer les nouvelles clés et mettre à jour .env
# 4. Changer permissions
chmod 600 copilot-app/backend/.env
```

### 10.4 Rollback des hooks Git

```bash
# Désinstaller les hooks
rm .git/hooks/pre-commit .git/hooks/pre-push .git/hooks/commit-msg

# Ou restaurer la version précédente
git checkout <commit-sûr> -- .githooks/
./scripts/install-git-hooks.sh
```

---

## 11. ✅ CHECKLIST DE SUIVI

```
[ ] Clés API révoquées et régénérées
[ ] Permissions .env changées en 600
[ ] .env.example créé avec valeurs factices
[ ] Plan d'action prioritaire validé par l'équipe
[ ] Date de revue de sécurité fixée (recommandé: mensuelle)
```

---

## 12. 📞 CONTACTS ET RÉFÉRENCES

- **Security Allowlist:** `SECURITY_ALLOWLIST.md`
- **Architecture:** `ARCHITECTURE_MAP.md`
- **Dépôt:** https://github.com/DelaaReda/app-finance-previsions

---

**Généré par:** Audit de Sécurité Automatisé  
**Date:** 2026-02-23  
**Prochaine revue recommandée:** 2026-03-23
