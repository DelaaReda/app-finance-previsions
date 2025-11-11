# 🔍 Guide d'Investigation Avancé - Finance Copilot

> ⚠️ **Document archivé** — Les commandes système directes (`lsof`, `kill -9`, etc.) mentionnées plus bas
> ne doivent plus être utilisées. Préférez toujours `./finance-copilot.sh stop|start|status`
> qui gère automatiquement les ports 8050/5173.

**Guide complet pour diagnostiquer et résoudre les problèmes dans Finance Copilot**  
**Version**: 2.0 - Enrichie avec techniques avancées  
**Dernière mise à jour**: 2025-01-27

---

## 📋 Table des Matières

1. [Investigation Loop](#investigation-loop)
2. [Launch & Baseline Checks](#launch--baseline-checks)
3. [Frontend Investigation Avancée](#frontend-investigation-avancée)
4. [Backend & Data Investigation Approfondie](#backend--data-investigation-approfondie)
5. [Troubleshooting Avancé](#troubleshooting-avancé)
6. [Performance & Profiling](#performance--profiling)
7. [Traçage End-to-End](#traçage-end-to-end)
8. [Patterns d'Erreurs Détaillés](#patterns-derreurs-détaillés)
9. [Testing & Proof](#testing--proof)

---

## Investigation Loop

### 🔄 Cycle d'Investigation Standard

1. **Reset** — utilisez toujours `finance-copilot.sh` pour démarrer/arrêter/status afin d'éviter les ports fantômes.
2. **Observer** — chargez la page UI ciblée, ouvrez DevTools (Console/Network) et capturez un screenshot de l'état actuel.
3. **Traquer la donnée** — interrogez les endpoints (`curl`), inspectez `data/*.json` et identifiez quel job/service alimente la vue.
4. **Implémenter** — mettez à jour le service/pipeline, régénérez la donnée (`load_or_compute`, jobs `jobs/*.py`), puis relancez le stack.
5. **Prouver** — re-capturez UI + curl, sauvegardez les preuves, mettez à jour `SCORE_AGENTS.md` et la doc associée.

**Principe fondamental** : Chaque boucle doit livrer un écran fonctionnel + données réelles, sans mocks ni placeholders.

---

### 🎯 Scénarios Types (Cheat Sheet)

| Constat | Réflexe Immédiat | Investigation Approfondie |
|---------|------------------|---------------------------|
| **Widget/dashboard vide** | 1⃣ `curl` l'endpoint (`/api/dashboard/kpis`). 2⃣ Ouvrir le hook (`useDashboard`). 3⃣ Inspecter `services/dashboard_service.py` + fichier `data/dashboard/*.json`. 4⃣ Relancer le job correspondant (`python jobs/dashboard_refresh.py --force`). | Voir [Pattern 1: Data Not Loading](#pattern-1-data-not-loading-diagnostic-complet) |
| **Page Macro bloquée en "Loading"** | 1⃣ DevTools Network → `/api/macro/series`. 2⃣ `curl` pour reproduire. 3⃣ Lire `useMacro.ts` pour connaître les params. 4⃣ Côté backend : route `api/main.py` → `services/macro_service.py` → `data/macro/`. | Voir [Pattern 2: Infinite Loading](#pattern-2-infinite-loading-diagnostic) |
| **LLM Judge timeout** | 1⃣ Récupérer le payload depuis l'UI. 2⃣ `curl` `/api/llm/judge/run`. 3⃣ Vérifier `api.log`. 4⃣ Mettre à jour `analytics/econ_llm_agent.py` ou relancer `python -m src.agents.g4f_model_watcher --refresh`. | Voir [Pattern 3: LLM Timeout](#pattern-3-llm-timeout-diagnostic) |
| **API 200 mais UI vide** | 1⃣ Network → Response JSON. 2⃣ Trouver le hook (`useNewsRadar`, `useStocksScreener`). 3⃣ Lire le mapping dans le hook (souvent `ensureArray`). 4⃣ Aligner le service backend + dataset pour exposer les mêmes champs. | Voir [Pattern 4: API 200 Empty Response](#pattern-4-api-200-empty-response) |
| **Page complètement blanche** | 1⃣ Console navigateur (F12) → chercher erreurs JavaScript. 2⃣ Vérifier imports/exports. 3⃣ Vérifier syntaxe JSX. 4⃣ Vérifier que React Router fonctionne. | Voir [Pattern 5: White Screen](#pattern-5-white-screen-of-death) |
| **Erreur de compilation TypeScript** | 1⃣ Lire première erreur (pas toutes). 2⃣ Vérifier types manquants. 3⃣ Vérifier imports. 4⃣ Vérifier exports. | Voir [Pattern 6: TypeScript Errors](#pattern-6-typescript-compilation-errors) |

---

## Launch & Baseline Checks

### 🔌 Vérification des Ports et Processus

#### Script Officiel (OBLIGATOIRE)

```bash
# Vérifier l'état complet du stack
/Users/venom/Documents/analyse-financiere/finance-copilot.sh status

# Arrêter proprement (libère tous les ports)
/Users/venom/Documents/analyse-financiere/finance-copilot.sh stop

# Redémarrer l'ensemble
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start

# Redémarrer avec nettoyage complet
/Users/venom/Documents/analyse-financiere/finance-copilot.sh restart
```

> ⚠️ **IMPORTANT** : Évitez toute commande système manuelle (`kill`, `lsof`, `pkill`). Le script encapsule toute la logique de nettoyage et évite les conflits de ports.

#### Diagnostic Avancé des Ports

> 🛑 **Obsolète** — Ces commandes sont conservées uniquement pour historique.
> Préférez `./finance-copilot.sh stop|start|status`.  
> N'utilisez le bloc ci-dessous **que pour lecture**.

```bash
# Vérifier quel processus utilise le port 5173 (frontend)
lsof -ti:5173

# Vérifier quel processus utilise le port 8050 (backend)
lsof -ti:8050

# Voir les détails complets
lsof -i:5173 -i:8050

# Tuer un processus spécifique (si vraiment nécessaire)
kill -9 $(lsof -ti:5173)
```

#### Vérification des Processus Background

```bash
# Lister tous les processus Node/Vite
ps aux | grep -E "vite|node" | grep -v grep

# Lister tous les processus Python API
ps aux | grep -E "uvicorn|run_api|python.*api" | grep -v grep

# Voir les processus avec détails (PID, CPU, mémoire)
ps aux | grep vite | awk '{print $2, $3, $4, $11}'

# Vérifier si un processus écoute sur un port
netstat -an | grep -E "5173|8050" | grep LISTEN
# OU (sur Linux moderne)
ss -tlnp | grep -E "5173|8050"
```

---

## Frontend Investigation Avancée

### 1. 🔍 Check Dev Server Status (Approfondi)

#### Vérification Basique

```bash
# Démarrer via script global
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start

# Vérifier que le frontend répond
curl -I http://localhost:5173

# Vérifier avec timeout
curl --max-time 5 http://localhost:5173
```

#### Diagnostic Avancé du Serveur Dev

```bash
# Vérifier les logs Vite en temps réel
tail -f copilot-app/frontend/webapp/frontend.log

# Vérifier la configuration Vite
cat copilot-app/frontend/webapp/vite.config.ts

# Vérifier les variables d'environnement
cat copilot-app/frontend/webapp/.env

# Purge complète du cache Vite
cd copilot-app/frontend/webapp
rm -rf node_modules/.vite
rm -rf dist
rm -rf .vite
# Puis relancer via script
/Users/venom/Documents/analyse-financiere/finance-copilot.sh restart
```

#### Vérification de la Configuration

```bash
# Vérifier tsconfig.json pour les path aliases
cat copilot-app/frontend/webapp/tsconfig.json | grep -A 10 "paths"

# Vérifier package.json pour les dépendances
cat copilot-app/frontend/webapp/package.json | grep -E "@mantine|@tremor|react"

# Vérifier que les dépendances sont installées
cd copilot-app/frontend/webapp
pnpm list --depth=0 | grep -E "@mantine|@tremor"
```

---

### 2. 🐛 Check for Compilation Errors (Détaillé)

#### Types d'Erreurs de Compilation

Le serveur dev affiche des erreurs de compilation. Voici comment les interpréter :

##### A. Import Errors

**Pattern** :
```
✘ [ERROR] No matching export in "src/ui/Ring.tsx" for import "Ring"
✘ [ERROR] Cannot find module '@/components/Something'
```

**Diagnostic** :
```bash
# 1. Vérifier que le fichier existe
find copilot-app/frontend/webapp/src -name "Ring.tsx"

# 2. Vérifier les exports dans le fichier
grep -n "export" copilot-app/frontend/webapp/src/ui/Ring.tsx

# 3. Vérifier les imports qui utilisent ce composant
grep -rn "import.*Ring" copilot-app/frontend/webapp/src/

# 4. Vérifier si c'est un problème de path alias
grep -rn "@/ui/Ring" copilot-app/frontend/webapp/src/
```

**Solutions** :
- Si `export default` mais import `{ Ring }` → changer en `export { Ring }` ou `export function Ring()`
- Si path alias `@/` ne fonctionne pas → vérifier `tsconfig.json` paths
- Si module non trouvé → vérifier `package.json` et `pnpm install`

##### B. Type Errors (TypeScript)

**Pattern** :
```
✘ [ERROR] Property 'items' does not exist on type 'undefined'
✘ [ERROR] Type 'string' is not assignable to type 'number'
```

**Diagnostic** :
```bash
# 1. Lire l'erreur complète (première erreur seulement)
# 2. Ouvrir le fichier mentionné à la ligne indiquée
cat -n copilot-app/frontend/webapp/src/pages/Dashboard.tsx | sed -n '50,70p'

# 3. Vérifier les types
grep -n "interface\|type" copilot-app/frontend/webapp/src/pages/Dashboard.tsx

# 4. Vérifier les imports de types
head -30 copilot-app/frontend/webapp/src/pages/Dashboard.tsx | grep import
```

**Solutions** :
- Ajouter des guards : `data?.items` au lieu de `data.items`
- Utiliser `safeArray()` : `const items = safeArray(data?.items)`
- Vérifier les types dans les interfaces
- Ajouter des assertions de type si nécessaire : `as Type`

##### C. JSX Syntax Errors

**Pattern** :
```
✘ [ERROR] Expected corresponding JSX closing tag for <div>
✘ [ERROR] Unexpected token, expected ","
```

**Diagnostic** :
```bash
# 1. Trouver les balises non fermées
grep -n "<Stack\|<Group\|<Card" copilot-app/frontend/webapp/src/components/NewsWidget.tsx
grep -n "</Stack\|</Group\|</Card" copilot-app/frontend/webapp/src/components/NewsWidget.tsx

# 2. Compter les ouvertures vs fermetures
grep -o "<Stack" copilot-app/frontend/webapp/src/components/NewsWidget.tsx | wc -l
grep -o "</Stack" copilot-app/frontend/webapp/src/components/NewsWidget.tsx | wc -l

# 3. Chercher les erreurs de syntaxe dans les props
grep -n "valueFormatter.*=>" copilot-app/frontend/webapp/src/components/visualizations/*.tsx
```

**Solutions** :
- Vérifier que toutes les balises sont fermées
- Vérifier les props (pas de template literals directs dans JSX)
- Extraire les fonctions de formatage : `const formatValue = (v) => ...` puis `valueFormatter={formatValue}`

##### D. Dependency Errors

**Pattern** :
```
✘ [ERROR] Cannot find module '@mantine/core'
✘ [ERROR] Module not found: Error: Can't resolve '@tremor/react'
```

**Diagnostic** :
```bash
# Vérifier que les packages sont dans package.json
cat copilot-app/frontend/webapp/package.json | grep "@mantine/core"

# Vérifier que node_modules existe
ls -la copilot-app/frontend/webapp/node_modules/@mantine/

# Réinstaller les dépendances
cd copilot-app/frontend/webapp
rm -rf node_modules
pnpm install
```

---

### 3. 🔎 Find Files by Pattern (Avancé)

```bash
# Find specific files (avec erreurs supprimées)
find copilot-app/frontend/webapp -name "Ring.tsx" -type f 2>/dev/null

# Find all TypeScript React files
find copilot-app/frontend/webapp/src -name "*.tsx" -type f | head -20

# Find files containing specific text (avec contexte)
grep -rn "NewsWidget" --include="*.tsx" copilot-app/frontend/webapp/src

# Find files by import pattern
grep -rn "from.*visualizations" --include="*.tsx" copilot-app/frontend/webapp/src

# Find files that export a specific component
grep -rn "export.*function.*MetricCard" --include="*.tsx" copilot-app/frontend/webapp/src

# List files in a directory with details
ls -lah copilot-app/frontend/webapp/src/components/widgets/

# Find largest files (peut indiquer des problèmes)
find copilot-app/frontend/webapp/src -name "*.tsx" -type f -exec ls -lh {} \; | sort -k5 -hr | head -10
```

---

### 4. 📄 Check File Contents (Techniques Avancées)

```bash
# Read a file with line numbers
cat -n copilot-app/frontend/webapp/src/ui/Ring.tsx

# Read first 50 lines
head -50 copilot-app/frontend/webapp/src/components/NewsWidget.tsx

# Read last 30 lines
tail -30 copilot-app/frontend/webapp/src/pages/Dashboard.tsx

# Read lines 50-100
sed -n '50,100p' copilot-app/frontend/webapp/src/pages/Dashboard.tsx

# Search for specific patterns in a file (avec contexte)
grep -n -A 5 -B 5 "export" copilot-app/frontend/webapp/src/ui/Ring.tsx

# Count occurrences
grep -c "import" copilot-app/frontend/webapp/src/pages/Dashboard.tsx

# Find all exports in a file
grep -n "export" copilot-app/frontend/webapp/src/ui/Ring.tsx

# Find all imports in a file
grep -n "^import" copilot-app/frontend/webapp/src/pages/Dashboard.tsx

# Extract interface/type definitions
grep -A 20 "interface.*Props" copilot-app/frontend/webapp/src/components/NewsWidget.tsx
```

---

### 5. 🖥️ Inspect Console Errors (Approfondi)

#### Setup DevTools

Après avoir démarré le serveur dev, ouvrez le navigateur DevTools (F12) et vérifiez :

##### A. Console Tab

**Erreurs Runtime Communes** :

1. **TypeError: Cannot read properties of undefined**
   ```
   TypeError: Cannot read properties of undefined (reading 'reduce')
   ```
   **Diagnostic** :
   - Notez le composant et la ligne (ex: `ForecastsMinimal.tsx:145`)
   - Ouvrez le fichier à cette ligne
   - Ajoutez des guards : `data?.rows?.reduce(...)` ou `safeArray(data?.rows).reduce(...)`

2. **ReferenceError: variable is not defined**
   ```
   ReferenceError: formatValue is not defined
   ```
   **Diagnostic** :
   - Vérifier que la fonction est définie avant d'être utilisée
   - Vérifier le scope (fonction vs composant)

3. **React Warning: validateDOMNesting**
   ```
   validateDOMNesting(...): <p> cannot appear as a descendant of <p>
   ```
   **Diagnostic** :
   ```bash
   # Chercher les Text imbriqués
   grep -rn "<Text.*<Text" copilot-app/frontend/webapp/src/components/
   ```
   **Solution** : Utiliser `<div>` au lieu de `<Text>` pour les conteneurs

##### B. Network Tab

**Vérifications** :

1. **Requêtes qui échouent (404, 500)**
   - Cliquez sur la requête → onglet "Response"
   - Vérifiez le message d'erreur
   - Vérifiez l'URL complète
   - Vérifiez les headers (Content-Type, Authorization si nécessaire)

2. **Requêtes qui timeout**
   - Vérifiez que le backend tourne
   - Vérifiez les logs backend
   - Augmentez le timeout si nécessaire

3. **Requêtes CORS**
   - Vérifiez que le proxy Vite est configuré
   - Vérifiez `vite.config.ts` pour les règles de proxy

##### C. Sources Tab

**Vérifications** :

1. **Fichiers non chargés**
   - Vérifiez que les fichiers sont dans `src/`
   - Vérifiez les imports
   - Vérifiez les path aliases

2. **Source maps**
   - Vérifiez que les source maps sont générées
   - Vérifiez `tsconfig.json` pour `sourceMap: true`

---

### 6. 🔗 Relier Composant → Hook → Service (Workflow Complet)

#### Étape 1: Identifier le Composant

```bash
# Trouver le composant qui affiche les données
# Exemple: NewsWidget affiche des news
grep -rn "NewsWidget" copilot-app/frontend/webapp/src/

# Lire le composant
cat copilot-app/frontend/webapp/src/components/widgets/NewsWidget.tsx
```

#### Étape 2: Trouver le Hook Utilisé

```bash
# Dans NewsWidget.tsx, chercher les hooks
grep -n "use.*" copilot-app/frontend/webapp/src/components/widgets/NewsWidget.tsx

# Exemple: useNewsRadar
# Trouver la définition du hook
find copilot-app/frontend/webapp/src -name "*useNewsRadar*" -o -name "*useNews*"

# Lire le hook
cat copilot-app/frontend/webapp/src/hooks/useNewsRadar.ts
```

#### Étape 3: Analyser le Hook

Dans le hook, identifier :
- L'endpoint appelé (ex: `/api/news/feed`)
- Les paramètres (ex: `limit`, `tickers`)
- Les transformations appliquées (ex: `ensureArray`, `map`)

```bash
# Vérifier l'API client utilisé
grep -n "apiGet\|apiPost\|fetch" copilot-app/frontend/webapp/src/hooks/useNewsRadar.ts

# Vérifier les transformations
grep -n "map\|filter\|reduce\|ensureArray" copilot-app/frontend/webapp/src/hooks/useNewsRadar.ts
```

#### Étape 4: Suivre l'API Client

```bash
# Lire le client API
cat copilot-app/frontend/webapp/src/api/client.ts

# Vérifier les retries/timeouts
grep -n "retry\|timeout" copilot-app/frontend/webapp/src/api/client.ts
```

#### Étape 5: Backend - Route → Service → Data

```bash
# 1. Trouver la route dans main.py
grep -n "/api/news" copilot-app/backend/src/api/main.py

# 2. Trouver le service appelé
grep -n "news_service\|get_news" copilot-app/backend/src/api/main.py

# 3. Lire le service
find copilot-app/backend/src -name "*news*service*" -o -name "*news*.py"

# 4. Vérifier la source de données
grep -n "data/news\|storage\|load_json" copilot-app/backend/src/services/news_service.py

# 5. Vérifier le fichier de données
ls -lh copilot-app/backend/data/news*.json
cat copilot-app/backend/data/news_feed.json | python3 -m json.tool | head -30
```

#### Étape 6: Corriger dans l'Ordre

**Ordre de correction** :
1. **Service/Pipeline** → Régénérer les données
2. **Dataset** → Vérifier la structure JSON
3. **Hook** → Aligner les transformations avec la structure
4. **Composant** → Afficher les données correctement

**Principe** : On ne "cache" jamais une donnée manquante via du front. Si la donnée n'existe pas, créer un pipeline (job + stockage) avant de modifier l'UI.

---

### 7. ✅ Évaluer la Qualité UI (Checklist Approfondie)

| Contrôle | Comment Faire | Ce qu'on Attend | Diagnostic Avancé |
|----------|----------------|-----------------|-------------------|
| **Loader vs. Empty state** | Inspecter `src/components/...` pour vérifier qu'un état "vide" existe (ex: `<EmptyState/>`). | Au lieu d'un spinner infini, afficher un message explicite (dernière mise à jour, CTA). | Vérifier que `isLoading` et `isEmpty` sont gérés séparément. Vérifier que `EmptyState` est importé et utilisé. |
| **Spacing / layout** | Utiliser DevTools → Inspect, vérifier marges/padding définis dans Mantine/Emotion. | Alignement cohérent avec `AppShell` (8 / 16 px). | Vérifier les tokens Mantine : `gap="md"`, `padding="lg"`. Vérifier qu'il n'y a pas de styles inline hardcodés. |
| **Typographie** | Vérifier tokens (`<Text fw="500" size="sm">`). | Titre H2 (fw 600), corps (fw 400). | Vérifier la hiérarchie : `Title order={1-6}`, `Text fw={400-700}`. Vérifier les couleurs : `c="dimmed"` pour secondaire. |
| **Données contextuelles** | Chaque carte doit montrer `updated_at`, ticker, unité. | Jamais de "N/A" sans explication. | Vérifier que les timestamps sont formatés. Vérifier que les unités sont affichées (% pour pourcentages, $ pour prix). |
| **Erreurs utilisateur** | Consulter Console : si `TypeError`, naviguer jusqu'à la ligne component. | Corriger avant capture/soumission. | Vérifier les guards : `data?.property`, `safeArray()`, `hasItems()`. Vérifier les fallbacks. |

🔍 **Astuce Avancée** : Pour comparer rapidement avant/après, ouvrir deux onglets, prendre screenshot de "état dégradé", puis de "état corrigé". Archivez les deux dans `proofs/...` pour montrer la progression.

---

## Backend & Data Investigation Approfondie

### 1. 🔌 Check Backend Server (Diagnostic Complet)

#### Vérification Basique

```bash
# Utiliser exclusivement le script global
/Users/venom/Documents/analyse-financiere/finance-copilot.sh status

# Vérifier manuellement si nécessaire
curl -s http://localhost:8050/api/health | python3 -m json.tool
```

#### Diagnostic Avancé

```bash
# Vérifier que le processus Python tourne
ps aux | grep -E "uvicorn|run_api" | grep -v grep

# Vérifier les logs backend en temps réel
tail -f copilot-app/backend/api.log

# Vérifier les logs avec filtrage
tail -f copilot-app/backend/api.log | grep -E "ERROR|WARNING|Exception"

# Vérifier la configuration
cat copilot-app/backend/src/api/main.py | grep -A 10 "app = FastAPI"

# Vérifier les variables d'environnement
cat copilot-app/backend/.env 2>/dev/null || echo "No .env file"
```

#### Vérification des Dépendances

```bash
# Vérifier que le venv est activé
which python
# Devrait pointer vers: copilot-app/backend/.venv/bin/python

# Vérifier les packages installés
source copilot-app/backend/.venv/bin/activate
pip list | grep -E "fastapi|uvicorn|pydantic"

# Vérifier les imports Python
python3 -c "import fastapi; print(fastapi.__version__)"
```

---

### 2. 🧪 Test API Endpoints (Techniques Avancées)

#### Tests Basiques

```bash
# Test health endpoint
curl -s http://localhost:8050/api/health | python3 -m json.tool

# Test specific endpoint
curl -s http://localhost:8050/api/forecasts | python3 -m json.tool | head -50

# Test with query parameters
curl -s "http://localhost:8050/api/news/feed?limit=5" | python3 -m json.tool

# Test and save response
curl -s http://localhost:8050/api/macro/series > macro_response.json
```

#### Tests Avancés

```bash
# Test avec verbose pour voir les headers
curl -v http://localhost:8050/api/health

# Test avec timeout
curl --max-time 10 http://localhost:8050/api/forecasts

# Test POST avec JSON
curl -X POST http://localhost:8050/api/llm/judge/run \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-ai/DeepSeek-V3-0324-Turbo", "tickers": "AAPL,MSFT"}' \
  | python3 -m json.tool

# Test avec authentification (si nécessaire)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8050/api/forecasts

# Mesurer le temps de réponse
time curl -s http://localhost:8050/api/forecasts > /dev/null

# Test de charge (simple)
for i in {1..10}; do curl -s http://localhost:8050/api/health > /dev/null; done
```

#### Validation des Réponses

```bash
# Vérifier que la réponse est du JSON valide
curl -s http://localhost:8050/api/forecasts | python3 -m json.tool > /dev/null && echo "✅ Valid JSON" || echo "❌ Invalid JSON"

# Vérifier la structure
curl -s http://localhost:8050/api/forecasts | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('Keys:', list(data.keys()))
print('Rows count:', len(data.get('rows', [])))
"

# Vérifier qu'il n'y a pas de données vides
curl -s http://localhost:8050/api/forecasts | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('rows', [])
if not rows:
    print('❌ Empty rows!')
    sys.exit(1)
else:
    print(f'✅ {len(rows)} rows found')
"
```

---

### 3. 🗺️ Check API Routes (Investigation Approfondie)

```bash
# Find all route files
find copilot-app/backend/src/api/routes -name "*.py" -type f

# Check which routes are defined
ls -la copilot-app/backend/src/api/routes/

# Read a route file
cat copilot-app/backend/src/api/routes/news.py | head -60

# Search for endpoint definitions
grep -rn "@router.get\|@router.post\|@app.get\|@app.post" copilot-app/backend/src/api/

# Find all registered routes dans main.py
grep -n "include_router\|app.include_router" copilot-app/backend/src/api/main.py

# Vérifier les préfixes de routes
grep -n "prefix=" copilot-app/backend/src/api/main.py

# Lister toutes les routes avec leurs méthodes
grep -rn "@router\." copilot-app/backend/src/api/routes/ | awk '{print $2}' | sort | uniq
```

#### Vérification de la Structure des Routes

```bash
# Vérifier qu'une route spécifique existe
grep -rn "/api/news/feed" copilot-app/backend/src/api/

# Vérifier les dépendances de routes
grep -rn "dependencies=\|Depends" copilot-app/backend/src/api/routes/

# Vérifier les middlewares
grep -rn "middleware\|@app.middleware" copilot-app/backend/src/api/main.py
```

---

### 4. 📋 Check Backend Logs (Analyse Approfondie)

#### Logs en Temps Réel

```bash
# Suivre les logs en temps réel
tail -f copilot-app/backend/api.log

# Suivre avec filtrage (erreurs seulement)
tail -f copilot-app/backend/api.log | grep -E "ERROR|WARNING|Exception|Traceback"

# Suivre avec contexte (5 lignes avant/après)
tail -f copilot-app/backend/api.log | grep -E "ERROR" -A 5 -B 5

# Suivre les logs d'un endpoint spécifique
tail -f copilot-app/backend/api.log | grep "/api/forecasts"
```

#### Analyse des Logs

```bash
# Compter les erreurs
grep -c "ERROR" copilot-app/backend/api.log

# Lister les dernières erreurs
grep "ERROR" copilot-app/backend/api.log | tail -20

# Extraire les stack traces
grep -A 20 "Traceback" copilot-app/backend/api.log | tail -50

# Analyser les patterns d'erreurs
grep "ERROR" copilot-app/backend/api.log | awk '{print $5}' | sort | uniq -c | sort -rn

# Vérifier les timeouts
grep -i "timeout\|timed out" copilot-app/backend/api.log | tail -10

# Vérifier les connexions refusées
grep -i "connection refused\|connection error" copilot-app/backend/api.log | tail -10
```

#### Logs Structurés

```bash
# Si les logs sont en JSON, utiliser jq
cat copilot-app/backend/api.log | jq 'select(.level == "ERROR")' | head -20

# Extraire les timestamps des erreurs
grep "ERROR" copilot-app/backend/api.log | awk '{print $1, $2}' | tail -20
```

---

### 5. 📊 Verify Data Files (Vérification Approfondie)

#### Vérification Basique

```bash
# Check if data files exist
ls -lh copilot-app/backend/data/

# Check file contents
head -30 copilot-app/backend/data/forecasts.json
head -30 copilot-app/backend/data/news_feed.json
cat copilot-app/backend/data/brief_weekly.json | python3 -m json.tool | head -40

# Check file timestamps
ls -lt copilot-app/backend/data/
```

#### Vérification Avancée

```bash
# Vérifier la taille des fichiers (ne doivent pas être vides)
find copilot-app/backend/data/ -name "*.json" -size 0

# Vérifier que les fichiers sont du JSON valide
for file in copilot-app/backend/data/*.json; do
    echo "Checking $file..."
    python3 -m json.tool "$file" > /dev/null && echo "✅ Valid" || echo "❌ Invalid"
done

# Vérifier la structure des données
cat copilot-app/backend/data/forecasts.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('Top-level keys:', list(data.keys()))
if 'rows' in data:
    print('Rows count:', len(data['rows']))
    if data['rows']:
        print('First row keys:', list(data['rows'][0].keys()))
"

# Vérifier les timestamps (fraîcheur des données)
cat copilot-app/backend/data/forecasts.json | python3 -c "
import json, sys
from datetime import datetime
data = json.load(sys.stdin)
if 'generated_at' in data:
    gen_time = datetime.fromisoformat(data['generated_at'].replace('Z', '+00:00'))
    now = datetime.now(gen_time.tzinfo)
    age = now - gen_time
    print(f'Data age: {age}')
"

# Compter les fichiers par type
find copilot-app/backend/data/ -name "*.json" | wc -l
find copilot-app/backend/data/ -name "*.parquet" | wc -l
```

---

### 6. 🔄 Map Data Gaps to Jobs/Pipelines (Workflow Complet)

#### Trouver la Source de Données

```bash
# Trouver quel service ou job manipule la ressource
rg -n "brief_weekly" copilot-app/backend/src/ copilot-app/backend/jobs/

# Inspecter les jobs disponibles
ls -la copilot-app/backend/jobs/

# Vérifier les jobs qui génèrent des données
grep -rn "save_json\|save_parquet\|storage.io" copilot-app/backend/jobs/

# Trouver les jobs qui utilisent un fichier spécifique
grep -rn "forecasts.json" copilot-app/backend/
```

#### Exécuter un Job

```bash
# Activer le venv
source copilot-app/backend/.venv/bin/activate

# Lister les jobs disponibles avec leurs options
python copilot-app/backend/jobs/risk_calculator.py --help

# Exécuter un job pour régénérer une donnée
python copilot-app/backend/jobs/risk_calculator.py --limit 250 --force

# Exécuter avec verbose
python copilot-app/backend/jobs/risk_calculator.py --limit 250 --force --verbose

# Vérifier les logs du job
tail -f copilot-app/backend/api.log | grep "risk_calculator"
```

#### Vérifier la Génération

```bash
# Vérifier que le fichier a été créé/modifié
ls -lh copilot-app/backend/data/risk_*.json

# Vérifier le timestamp
stat -c "%y" copilot-app/backend/data/risk_calculator.json

# Vérifier le contenu
cat copilot-app/backend/data/risk_calculator.json | python3 -m json.tool | head -30
```

> ⚠️ **Rappel Important** : Si la donnée affichée dans l'UI n'existe pas dans `data/` ou via un endpoint, mettez à jour le service dans `copilot-app/backend/src/services/` et sauvegardez la sortie avec `storage.io`. Le frontend ne doit jamais dépendre de mocks temporaires.

---

### 7. 💾 Persister et Vérifier (Workflow Complet)

#### Code Python pour Persister

```python
from storage import io
payload = {
    "generated_at": datetime.utcnow().isoformat(),
    "rows": rows,
    "count": len(rows)
}
io.save_json("dashboard/kpis", payload)  # écrit data/dashboard/kpis.json
```

#### Vérification

```bash
# 1. Vérifier que le fichier a été créé
ls -lh copilot-app/backend/data/dashboard/kpis.json

# 2. Vérifier le contenu
cat copilot-app/backend/data/dashboard/kpis.json | python3 -m json.tool | head -20

# 3. Vérifier la structure
cat copilot-app/backend/data/dashboard/kpis.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
required_keys = ['generated_at', 'rows', 'count']
missing = [k for k in required_keys if k not in data]
if missing:
    print(f'❌ Missing keys: {missing}')
    sys.exit(1)
else:
    print('✅ All required keys present')
    print(f'Rows: {len(data.get(\"rows\", []))}')
"

# 4. Noter dans le proof quel job a été relancé
echo "Job: dashboard_refresh.py --force" > proofs/.../job_log.txt
```

---

### 8. 📝 Missing Data Playbook (Pas à Pas Détaillé)

#### Étape 1: Détecter l'Absence

```bash
# UI vide → noter le composant/hook
# Exemple: Dashboard affiche "No data"

# curl l'endpoint correspondant
curl -s http://localhost:8050/api/dashboard/kpis > proofs/before.json

# Vérifier la réponse
cat proofs/before.json | python3 -m json.tool

# Si la réponse est vide ou erreur, noter
echo "Before fix: Empty response" >> proofs/before.json
```

#### Étape 2: Isoler la Source

```bash
# Trouver où le champ est produit
rg -n "dashboard.*kpis\|get_kpis" copilot-app/backend/src/

# Vérifier si data/dashboard/ contient la clé
ls -la copilot-app/backend/data/dashboard/

# Vérifier le contenu
cat copilot-app/backend/data/dashboard/kpis.json 2>/dev/null || echo "File does not exist"

# Si le fichier existe mais est vide
cat copilot-app/backend/data/dashboard/kpis.json | python3 -m json.tool | head -5
```

#### Étape 3: Régénérer

```bash
# Activer le venv
source copilot-app/backend/.venv/bin/activate

# Lancer le job ciblé
python copilot-app/backend/jobs/dashboard_refresh.py --force --tickers SPY,QQQ

# Surveiller api.log pour confirmer l'écriture
tail -f copilot-app/backend/api.log | grep -E "dashboard|kpis|save_json"

# Vérifier que le fichier a été créé/modifié
ls -lh copilot-app/backend/data/dashboard/kpis.json
stat -c "%y" copilot-app/backend/data/dashboard/kpis.json
```

#### Étape 4: Valider Structure

```bash
# Utiliser jq pour valider
cat copilot-app/backend/data/dashboard/kpis.json | jq '.' | head -50

# Comparer avec ce qu'attend le hook
# Lire le hook frontend
cat copilot-app/frontend/webapp/src/hooks/useDashboard.ts

# Vérifier les champs attendus
cat copilot-app/frontend/webapp/src/hooks/useDashboard.ts | grep -A 10 "data\."

# Si transformation nécessaire, ajuster le service
# Exemple: return {"rows": rows, "count": len(rows)}
```

#### Étape 5: Propager jusqu'au Front

```bash
# Redémarrer stack
/Users/venom/Documents/analyse-financiere/finance-copilot.sh restart

# Vider caches frontend si nécessaire
rm -rf copilot-app/frontend/webapp/node_modules/.vite

# Vérifier localStorage (si utilisé)
# Dans DevTools → Application → Local Storage
```

#### Étape 6: Preuve

```bash
# curl après fix
curl -s http://localhost:8050/api/dashboard/kpis > proofs/after.json

# Screenshot UI mis à jour
# Utiliser l'outil de capture dans tests/finance_app_test-v2.html

# Mettre à jour SCORE_AGENTS.md
echo "Missing data resolved – Dashboard page" >> SCORE_AGENTS.md
```

> ⚠️ **Rappel Fondamental** : Jamais de valeur "mockée" dans les services. Si la donnée n'existe pas, créez un pipeline (job + stockage) avant de modifier l'UI.

---

## Troubleshooting Avancé

### 🔍 Techniques de Diagnostic Approfondies

#### 1. Traçage des Appels de Fonction

```bash
# Backend Python - Ajouter des prints de debug
# Dans le service, ajouter:
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Function called with args: {args}")

# Vérifier les logs
tail -f copilot-app/backend/api.log | grep "DEBUG"

# Frontend - Utiliser console.log stratégiquement
# Dans le hook, ajouter:
console.log('[useForecasts] Data received:', data);
console.log('[useForecasts] Transformed:', transformed);
```

#### 2. Breakpoints et Debugging

**Backend (Python)** :
```python
# Utiliser pdb (Python Debugger)
import pdb; pdb.set_trace()  # Arrête l'exécution ici

# Ou utiliser ipdb (plus avancé)
import ipdb; ipdb.set_trace()
```

**Frontend (React)** :
- Utiliser les DevTools → Sources → Breakpoints
- Utiliser `debugger;` dans le code
- Utiliser React DevTools pour inspecter les props/state

#### 3. Vérification des Versions

```bash
# Backend
source copilot-app/backend/.venv/bin/activate
python --version
pip list | grep -E "fastapi|uvicorn|pydantic"

# Frontend
cd copilot-app/frontend/webapp
node --version
pnpm --version
cat package.json | grep -E "react|@mantine|@tremor"
```

---

## Performance & Profiling

### ⚡ Diagnostic de Performance

#### Backend Performance

```bash
# Mesurer le temps de réponse d'un endpoint
time curl -s http://localhost:8050/api/forecasts > /dev/null

# Profiler Python avec cProfile
python -m cProfile -o profile.stats copilot-app/backend/src/api/main.py

# Analyser le profil
python -m pstats profile.stats
# Dans pstats: sort cumulative, stats 20

# Utiliser py-spy pour profiling en temps réel
py-spy record -o profile.svg --pid $(pgrep -f "uvicorn")
```

#### Frontend Performance

```bash
# Utiliser Lighthouse (via Chrome DevTools)
# DevTools → Lighthouse → Run audit

# Utiliser React Profiler
# DevTools → Profiler → Record

# Vérifier les bundle sizes
cd copilot-app/frontend/webapp
pnpm build
ls -lh dist/assets/*.js | sort -k5 -hr | head -10
```

---

## Traçage End-to-End

### 🔄 Workflow de Traçage Complet

#### 1. Frontend → API Call

```bash
# Dans DevTools → Network, trouver la requête
# Noter: URL, Method, Headers, Payload

# Reproduire avec curl
curl -X POST http://localhost:8050/api/llm/judge/run \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-ai/DeepSeek-V3-0324-Turbo", "tickers": "AAPL"}' \
  -v
```

#### 2. Backend → Service → Data

```bash
# Vérifier les logs backend
tail -f copilot-app/backend/api.log | grep "judge"

# Vérifier le service appelé
grep -rn "judge/run" copilot-app/backend/src/api/

# Vérifier la source de données
grep -rn "forecasts\|get_forecasts" copilot-app/backend/src/services/
```

#### 3. Data → Response → Frontend

```bash
# Vérifier la réponse API
curl -s http://localhost:8050/api/forecasts | python3 -m json.tool > response.json

# Vérifier que le hook transforme correctement
cat copilot-app/frontend/webapp/src/hooks/useForecasts.ts

# Vérifier que le composant affiche correctement
cat copilot-app/frontend/webapp/src/pages/ForecastsMinimal.tsx
```

---

## Patterns d'Erreurs Détaillés

### Pattern 1: Data Not Loading (Diagnostic Complet)

**Symptômes** :
- UI affiche "Loading..." indéfiniment
- UI affiche "No data" mais l'API retourne 200
- Données partielles ou incomplètes

**Diagnostic Étape par Étape** :

1. **Vérifier l'API** :
```bash
curl -v http://localhost:8050/api/forecasts
# Vérifier: Status 200, Content-Type: application/json, Body non vide
```

2. **Vérifier le Hook** :
```bash
# Lire le hook
cat copilot-app/frontend/webapp/src/hooks/useForecasts.ts

# Vérifier:
# - L'endpoint est correct
# - Les paramètres sont passés
# - Les transformations sont correctes
# - Les guards sont en place (data?.rows)
```

3. **Vérifier le Composant** :
```bash
# Lire le composant
cat copilot-app/frontend/webapp/src/pages/ForecastsMinimal.tsx

# Vérifier:
# - isLoading est géré
# - error est géré
# - data?.rows est utilisé (pas data.rows)
# - EmptyState est affiché si nécessaire
```

4. **Vérifier les Données Backend** :
```bash
# Vérifier le fichier de données
ls -lh copilot-app/backend/data/forecasts.json
cat copilot-app/backend/data/forecasts.json | python3 -m json.tool | head -20

# Vérifier le service
grep -rn "forecasts" copilot-app/backend/src/services/
```

**Solutions** :
- Si API retourne 200 mais vide → Régénérer les données (job)
- Si API retourne erreur → Vérifier les logs backend
- Si hook ne transforme pas → Aligner avec la structure backend
- Si composant crash → Ajouter des guards

---

### Pattern 2: Infinite Loading (Diagnostic)

**Symptômes** :
- Spinner infini
- Pas d'erreur dans la console
- Network tab montre requête en "pending"

**Diagnostic** :

1. **Vérifier la Requête Network** :
```bash
# Dans DevTools → Network
# Vérifier: Status (pending, 200, 404, 500)
# Vérifier: Time (si > 30s, timeout probable)
```

2. **Vérifier le Backend** :
```bash
# Vérifier que le backend répond
curl -s http://localhost:8050/api/health

# Vérifier les logs
tail -f copilot-app/backend/api.log | grep "ERROR\|WARNING"
```

3. **Vérifier le Timeout** :
```bash
# Dans le hook, vérifier le timeout
grep -n "timeout\|staleTime" copilot-app/frontend/webapp/src/hooks/useForecasts.ts

# Dans l'API client, vérifier le timeout
grep -n "timeout" copilot-app/frontend/webapp/src/api/client.ts
```

**Solutions** :
- Si timeout → Augmenter le timeout ou optimiser le backend
- Si backend ne répond pas → Vérifier que le serveur tourne
- Si requête bloque → Vérifier les CORS/proxy

---

### Pattern 3: LLM Timeout (Diagnostic)

**Symptômes** :
- LLM Judge retourne 503
- Message: "no answer from dynamic model selector"
- Timeout après plusieurs tentatives

**Diagnostic** :

1. **Vérifier les Modèles** :
```bash
# Vérifier les modèles disponibles
grep -n "VERIFIED.*MODELS" copilot-app/backend/src/api/main.py

# Vérifier le watcher G4F
python -m copilot-app.backend.src.agents.g4f_model_watcher --list
```

2. **Vérifier les Logs** :
```bash
# Chercher les erreurs LLM
tail -f copilot-app/backend/api.log | grep -E "LLM|g4f|model.*failed"
```

3. **Tester un Modèle Directement** :
```bash
# Tester avec curl
curl -X POST http://localhost:8050/api/llm/judge/run \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "tickers": "AAPL"}' \
  -v
```

**Solutions** :
- Si tous les modèles échouent → Vérifier la connexion internet
- Si un modèle spécifique échoue → Retirer de la liste ou corriger
- Si timeout → Augmenter le timeout ou utiliser un modèle plus rapide

---

### Pattern 4: API 200 Empty Response

**Symptômes** :
- API retourne 200 OK
- Body: `{"rows": []}` ou `{}`
- UI affiche "No data"

**Diagnostic** :

1. **Vérifier la Réponse** :
```bash
curl -s http://localhost:8050/api/forecasts | python3 -m json.tool

# Vérifier:
# - Structure: {"rows": [...]} ou autre?
# - rows est un array (même vide)
# - Pas de null ou undefined
```

2. **Vérifier le Hook** :
```bash
# Vérifier comment le hook traite la réponse
cat copilot-app/frontend/webapp/src/hooks/useForecasts.ts

# Vérifier:
# - ensureArray(data?.rows) ou data?.rows || []
# - Les transformations sont correctes
```

3. **Vérifier les Données Backend** :
```bash
# Vérifier le fichier source
cat copilot-app/backend/data/forecasts.json | python3 -m json.tool

# Vérifier le service
grep -rn "forecasts" copilot-app/backend/src/services/
```

**Solutions** :
- Si rows est vide → Régénérer les données (job)
- Si structure différente → Aligner backend et frontend
- Si hook ne gère pas → Ajouter des guards et fallbacks

---

### Pattern 5: White Screen of Death

**Symptômes** :
- Page complètement blanche
- Pas de contenu affiché
- Console peut avoir des erreurs

**Diagnostic** :

1. **Vérifier la Console** :
```bash
# Dans DevTools → Console
# Chercher:
# - Erreurs JavaScript (rouge)
# - Warnings (jaune)
# - Erreurs de compilation
```

2. **Vérifier les Imports** :
```bash
# Vérifier les imports dans le composant principal
head -30 copilot-app/frontend/webapp/src/App.tsx | grep import

# Vérifier les exports
grep -n "export" copilot-app/frontend/webapp/src/App.tsx
```

3. **Vérifier React Router** :
```bash
# Vérifier que les routes sont définies
grep -n "Route\|router" copilot-app/frontend/webapp/src/App.tsx

# Vérifier que le composant de page existe
find copilot-app/frontend/webapp/src/pages -name "Dashboard.tsx"
```

4. **Vérifier les Erreurs de Syntaxe** :
```bash
# Vérifier la compilation
cd copilot-app/frontend/webapp
pnpm build 2>&1 | head -50
```

**Solutions** :
- Si erreur d'import → Corriger l'import ou créer le fichier manquant
- Si erreur de syntaxe → Corriger la syntaxe JSX/TypeScript
- Si erreur React → Vérifier les hooks et les règles React
- Si erreur de route → Vérifier que la route et le composant existent

---

### Pattern 6: TypeScript Compilation Errors

**Symptômes** :
- Erreurs de compilation TypeScript
- Types manquants ou incorrects
- Imports non résolus

**Diagnostic** :

1. **Lire la Première Erreur** :
```bash
# Ne pas lire toutes les erreurs, seulement la première
# L'erreur suivante peut être causée par la première
```

2. **Vérifier les Types** :
```bash
# Vérifier les interfaces/types
grep -n "interface\|type" copilot-app/frontend/webapp/src/components/NewsWidget.tsx

# Vérifier les imports de types
head -30 copilot-app/frontend/webapp/src/components/NewsWidget.tsx | grep import
```

3. **Vérifier tsconfig.json** :
```bash
# Vérifier la configuration
cat copilot-app/frontend/webapp/tsconfig.json

# Vérifier les path aliases
cat copilot-app/frontend/webapp/tsconfig.json | grep -A 10 "paths"
```

**Solutions** :
- Si type manquant → Ajouter le type ou utiliser `any` temporairement
- Si import non résolu → Vérifier le path alias ou le chemin relatif
- Si type incorrect → Corriger le type ou utiliser une assertion

---

## Testing & Proof

### 1. After Frontend Changes

```bash
# Touch file to force reload
touch copilot-app/frontend/webapp/src/components/NewsWidget.tsx

# Restart dev server with clean cache
cd copilot-app/frontend/webapp
rm -rf node_modules/.vite && pnpm dev

# Check if error is gone in terminal output
# Check if browser console is clean
# Test the specific page/component
```

**Capturer les Preuves UI** :
1. Ouvrir `copilot-app/frontend/webapp/tests/finance_app_test-v2.html` dans le navigateur.
2. Cliquer sur **Load Page** (ex: `http://localhost:5173/judge`), puis sur **Capture Screenshot**.
3. Sauvegarder l'image dans `proofs/UI-AUDIT-<YYYYMMDD>/` et référencer dans `SCORE_AGENTS.md`.

---

### 2. After Backend Changes

```bash
# Redémarrer le backend via le script global
/Users/venom/Documents/analyse-financiere/finance-copilot.sh restart

# Régénérer la donnée si nécessaire
source copilot-app/backend/.venv/bin/activate
python copilot-app/backend/jobs/calendar_ingest.py --limit 200 --force

# Tester l'endpoint à nouveau
curl -s http://localhost:8050/api/news/feed | python3 -m json.tool
```

---

### 3. Verify Full Flow

```bash
# 1. Backend is running
curl -s http://localhost:8050/api/health

# 2. Frontend is running
curl -s http://localhost:5173

# 3. Test API calls from frontend
# Open browser DevTools → Network tab
# Navigate to page and check:
# - All API calls return 200 status
# - Response data is correct
# - No console errors
```

---

### 4. Preuve & Scoreboard (Toujours Requis)

1. `mkdir -p proofs/UI-AUDIT-$(date +%Y%m%d)` puis déposer captures + JSON + logs.
2. Sauvegarder la réponse API (`curl ... | jq '.' > proofs/.../api-response.json`).
3. Copier l'extrait de `api.log` pertinent (`tail -n 50 copilot-app/backend/api.log > proofs/.../api.log.txt`).
4. Mettre à jour `SCORE_AGENTS.md` avec la mission (pages/testés, points, preuve).
5. Vérifier avec `git status` que preuves + scoreboard sont inclus avant commit.

---

## Quick Reference Commands

```bash
# Stack complet (ports/serveurs gérés automatiquement)
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start
/Users/venom/Documents/analyse-financiere/finance-copilot.sh stop
/Users/venom/Documents/analyse-financiere/finance-copilot.sh restart
/Users/venom/Documents/analyse-financiere/finance-copilot.sh status

# Find files
find copilot-app/frontend/webapp/src -name "*.tsx" -type f
grep -rn "import.*Component" copilot-app/frontend/webapp/src/

# Test API
curl -s http://localhost:8050/api/news/feed | python3 -m json.tool

# Check data
ls -lh copilot-app/backend/data/
cat copilot-app/backend/data/news_feed.json | python3 -m json.tool | head -30

# Check logs
tail -f copilot-app/backend/api.log | grep -E "ERROR|WARNING"
```

---

## Pro Tips Avancés

1. **Utiliser `python3 -m json.tool`** pour pretty-print JSON responses
2. **Utiliser `head` et `tail`** pour éviter overwhelming output
3. **Utiliser `grep -n`** pour obtenir les numéros de ligne dans les résultats
4. **Utiliser `2>/dev/null`** pour supprimer les messages d'erreur non nécessaires
5. **Garder les terminaux organisés** - un pour frontend, un pour backend, un pour commandes
6. **Utiliser `curl -s`** (silent) pour éviter les progress meters dans la sortie
7. **Pip to `less`** pour long output: `curl ... | less`
8. **Utiliser `&&`** pour chaîner les commandes qui dépendent les unes des autres
9. **Background processes** avec `&` mais les monitorer avec `jobs`
10. **Toujours vérifier backend ET frontend** - les problèmes peuvent être de chaque côté
11. **Utiliser `rg` (ripgrep)** au lieu de `grep` pour des recherches plus rapides
12. **Utiliser `jq`** pour manipuler JSON en ligne de commande
13. **Utiliser `time`** pour mesurer le temps d'exécution
14. **Utiliser `watch`** pour surveiller les changements en temps réel
15. **Documenter chaque fix** dans `proofs/` avec avant/après

---

## Created: 2025-11-07
## Last Updated: 2025-01-27
## Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
## Version: 2.0 - Enrichie avec techniques avancées
