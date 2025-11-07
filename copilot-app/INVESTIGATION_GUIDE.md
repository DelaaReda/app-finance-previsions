# Frontend/Backend Investigation Guide

This guide documents the CLI commands and process used to diagnose and fix issues in the Finance Copilot application.

## Table of Contents
1. [Investigation Loop](#investigation-loop)
2. [Launch & Baseline Checks](#launch--baseline-checks)
3. [Frontend Investigation](#frontend-investigation)
4. [Backend & Data Investigation](#backend--data-investigation)
5. [Finding and Fixing Code Issues](#finding-and-fixing-code-issues)
6. [Testing & Proof](#testing--proof)

---

## Investigation Loop

1. **Reset** — utilisez toujours `finance-copilot.sh` pour démarrer/arrêter/status afin d’éviter les ports fantômes.
2. **Observer** — chargez la page UI ciblée, ouvrez DevTools (Console/Network) et capturez un screenshot de l’état actuel.
3. **Traquer la donnée** — interrogez les endpoints (`curl`), inspectez `data/*.json` et identifiez quel job/service alimente la vue.
4. **Implémenter** — mettez à jour le service/pipeline, régénérez la donnée (`load_or_compute`, jobs `jobs/*.py`), puis relancez le stack.
5. **Prouver** — re-capturez UI + curl, sauvegardez les preuves, mettez à jour `SCORE_AGENTS.md` et la doc associée.

Chaque boucle doit livrer un écran fonctionnel + données réelles, sans mocks ni placeholders.

---

## Launch & Baseline Checks

### Find processes using specific ports
Les ports 5173 (frontend) et 8050 (backend) sont gérés par `finance-copilot.sh`.  
Utilisez exclusivement ce script pour démarrer/arrêter et libérer les ports :
```bash
/Users/venom/Documents/analyse-financiere/finance-copilot.sh status   # Vérifie backend+frontend
/Users/venom/Documents/analyse-financiere/finance-copilot.sh stop     # Arrête proprement (libère les ports)
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start    # Redémarre l'ensemble
```
> Évitez toute commande système manuelle : le script encapsule toute la logique de nettoyage.

### Check background dev servers
```bash
# List all node/vite processes
ps aux | grep vite

# List all python API processes
ps aux | grep run_api
```

---

## Frontend Investigation

### 1. Check Dev Server Status

```bash
# Démarrer ou redémarrer via le script global (frontend + backend)
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start

# Vérifier que le frontend répond
curl -I http://localhost:5173

# Purge du cache Vite si nécessaire (ensuite relancer via le script)
cd copilot-app/frontend/webapp
rm -rf node_modules/.vite
/Users/venom/Documents/analyse-financiere/finance-copilot.sh restart
```

### 2. Check for Compilation Errors

The dev server output will show compilation errors. Look for:
- **Import errors**: `Cannot find module` or `No matching export`
- **Type errors**: TypeScript compilation issues
- **JSX errors**: Invalid JSX syntax
- **Dependency errors**: Missing packages

Example error patterns:
```
✘ [ERROR] No matching export in "src/ui/Ring.tsx" for import "Ring"
✘ [ERROR] Expected corresponding JSX closing tag for <div>
```

### 3. Find Files by Pattern

```bash
# Find specific files
find . -name "Ring.tsx" -type f 2>/dev/null

# Find all TypeScript React files
find . -name "*.tsx" -type f | head -20

# Search for files containing specific text
grep -r "NewsWidget" --include="*.tsx" .

# List files in a directory
ls src/components/widgets/
```

### 4. Check File Contents

```bash
# Read a file with line numbers
cat -n src/ui/Ring.tsx

# Read first 50 lines
head -50 src/components/NewsWidget.tsx

# Read last 30 lines
tail -30 src/pages/Dashboard.tsx

# Search for specific patterns in a file
grep "export" src/ui/Ring.tsx
```

### 5. Inspect Console Errors

After starting the dev server, open browser DevTools (F12) and check:
- **Console** tab for runtime errors
- **Network** tab for failed API calls
- **Sources** tab to see which files are loaded

Common error patterns:
```
validateDOMNesting(...): <p> cannot appear as a descendant of <p>
Cannot read properties of undefined (reading 'reduce')
Failed to load resource: net::ERR_CONNECTION_REFUSED
```

---

## Backend Investigation

### 1. Check Backend Server

```bash
# Utiliser exclusivement le script global pour gérer le backend
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start   # démarrage
/Users/venom/Documents/analyse-financiere/finance-copilot.sh stop    # arrêt propre
/Users/venom/Documents/analyse-financiere/finance-copilot.sh status  # vérifie /api/health
```

### 2. Test API Endpoints

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

### 3. Check API Routes

```bash
# Find all route files
find ./api/routes -name "*.py" -type f

# Check which routes are defined
ls -la api/routes/

# Read a route file
cat api/routes/news.py | head -60

# Search for endpoint definitions
grep -r "@router.get" api/routes/
```

### 4. Check Backend Logs

```bash
# If running in background, check logs
tail -f /path/to/api.log

# Or check the terminal where backend is running
# Look for:
# - "✅ Successfully registered routes"
# - "INFO: Uvicorn running on http://..."
# - Any error messages or stack traces
```

### 5. Verify Data Files

```bash
# Check if data files exist
ls -lh data/

# Check file contents
head -30 data/forecasts.json
head -30 data/news_feed.json
cat data/brief_weekly.json | python3 -m json.tool | head -40

# Check file timestamps
ls -lt data/
```

### 6. Map Data Gaps to Jobs/Pipelines

```bash
# Trouver quel service ou job manipule la ressource
rg -n "brief_weekly" -n src/ jobs/ services/

# Inspecter les jobs disponibles
ls copilot-app/backend/jobs

# Exécuter un job pour régénérer une donnée
source copilot-app/backend/.venv/bin/activate
python copilot-app/backend/jobs/risk_calculator.py --limit 250 --force
```

> Si la donnée affichée dans l’UI n’existe pas dans `data/` ou via un endpoint, mettez à jour le service dans `copilot-app/backend/src/services/` et sauvegardez la sortie avec `storage.io`. Le frontend ne doit jamais dépendre de mocks temporaires.

---

## Finding and Fixing Code Issues

### 1. Locate Import/Export Issues

```bash
# Find where a component is exported
grep -n "export.*Ring" src/ui/Ring.tsx

# Find where a component is imported
grep -rn "import.*Ring" src/

# Check for default vs named exports
grep -A5 "export default" src/ui/Ring.tsx
grep -A5 "export {" src/ui/Ring.tsx
```

### 2. Find JSX Syntax Issues

```bash
# Look for unclosed tags
grep -n "<Stack" src/components/NewsWidget.tsx
grep -n "</Stack>" src/components/NewsWidget.tsx

# Check for nested components
grep -B2 -A2 "<Text.*<Text" src/components/
```

### 3. Find Component Dependencies

```bash
# Check what a component imports
head -20 src/components/widgets/NewsWidget.tsx | grep import

# Find all uses of a specific component
grep -rn "FreshnessBadge" src/

# Check package.json for installed packages
cat package.json | grep "@mantine/core"
```

### 4. Search Project Structure

```bash
# Get project structure
tree -L 3 -I 'node_modules|.git'

# Count TypeScript files
find . -name "*.tsx" -o -name "*.ts" | wc -l

# Find largest files
find . -name "*.tsx" -type f -exec ls -lh {} \; | sort -k5 -hr | head -10
```

---

## Testing & Proof

### 1. After Frontend Changes

```bash
# Touch file to force reload
touch src/components/NewsWidget.tsx

# Restart dev server with clean cache
rm -rf node_modules/.vite && pnpm dev

# Check if error is gone in terminal output
# Check if browser console is clean
# Test the specific page/component
```

**Capturer les preuves UI**
1. Ouvrir `copilot-app/frontend/webapp/tests/finance_app_test-v2.html` dans le navigateur.
2. Cliquer sur **Load Page** (ex: `http://localhost:5173/judge`), puis sur **Capture Screenshot** (intègre html2canvas).
3. Sauvegarder l’image dans `proofs/UI-AUDIT-<YYYYMMDD>/` et référencer le fichier dans `SCORE_AGENTS.md`.

### 2. After Backend Changes

```bash
# Redémarrer le backend via le script global (gère l'arrêt/redémarrage propre)
/Users/venom/Documents/analyse-financiere/finance-copilot.sh restart

# Régénérer la donnée si nécessaire (ex: job calendrier, risk, news...)
source copilot-app/backend/.venv/bin/activate
python copilot-app/backend/jobs/calendar_ingest.py --limit 200 --force

# Tester l'endpoint à nouveau
curl -s http://localhost:8050/api/news/feed | python3 -m json.tool
```

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

# 4. Log proofs & score
mkdir -p proofs/UI-AUDIT-$(date +%Y%m%d)
# (copiez vos captures + sorties curl ici)
vim SCORE_AGENTS.md   # consignez la mission + points
```

---

## Common Investigation Patterns

### Pattern 1: "Component Not Found" Error

```bash
# Step 1: Find where component is defined
find . -name "Ring.tsx"

# Step 2: Check exports in that file
grep "export" src/ui/Ring.tsx

# Step 3: Check imports in files using it
grep -rn "import.*Ring" src/components/

# Step 4: Verify export matches import
# If importing: import { Ring } from '@/ui/Ring'
# Then need: export { Ring } or export function Ring()
```

### Pattern 2: "API Not Responding" Error

```bash
# Step 1: Check if backend is running
/Users/venom/Documents/analyse-financiere/finance-copilot.sh status

# Step 2: Test endpoint directly
curl -v http://localhost:8050/api/news/feed

# Step 3: Check backend logs for errors
# (in terminal where backend is running)

# Step 4: Verify route is registered
grep -r "news" api/main.py
```

### Pattern 3: "Data Not Loading" Error

```bash
# Step 1: Check API endpoint
curl -s http://localhost:8050/api/news/feed | python3 -m json.tool

# Step 2: Check data file exists
ls -lh data/news_feed.json

# Step 3: Verify data structure
cat data/news_feed.json | python3 -m json.tool | head -50

# Step 4: Check frontend API call
# Open browser DevTools → Network tab
# Look for the /api/news/feed request
```

### Pattern 4: "React Warning in Console"

```bash
# Step 1: Note the component mentioned in warning
# Example: "at NewsWidget (NewsWidget.tsx:22:47)"

# Step 2: Open that file and line
cat -n src/components/widgets/NewsWidget.tsx | sed -n '20,70p'

# Step 3: Look for the specific issue
# For "validateDOMNesting", look for nested <p> or <Text> tags
grep -A3 -B3 "<Text.*<Text" src/components/widgets/NewsWidget.tsx
```

---

## Quick Reference Commands

```bash
# Frontend (utiliser pnpm uniquement pour du debug ciblé, sinon passer par finance-copilot.sh)
cd copilot-app/frontend/webapp
pnpm dev                              # Start dev server
rm -rf node_modules/.vite && pnpm dev # Clean restart

# Stack complet (ports/serveurs gérés automatiquement)
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start
/Users/venom/Documents/analyse-financiere/finance-copilot.sh stop
/Users/venom/Documents/analyse-financiere/finance-copilot.sh restart
/Users/venom/Documents/analyse-financiere/finance-copilot.sh status

# Find files
find . -name "*.tsx" -type f         # Find all TSX files
grep -rn "import.*Component" src/    # Find imports

# Test API
curl -s http://localhost:8050/api/news/feed | python3 -m json.tool

# Check data
ls -lh data/
cat data/news_feed.json | python3 -m json.tool | head -30

# Kill processes → utiliser uniquement le script global
/Users/venom/Documents/analyse-financiere/finance-copilot.sh stop
```

---

## Troubleshooting Workflow

1. **Identify the Issue**
   - Read error message carefully
   - Note file names, line numbers, component names

2. **Locate the Source**
   - Use `find` to locate files
   - Use `grep` to search for patterns
   - Use `cat` or `head` to read files

3. **Understand the Context**
   - Check related files
   - Verify imports/exports
   - Check API endpoints
   - Inspect data files

4. **Test the Fix**
   - Make changes
   - Restart servers
   - Test in browser
   - Verify no new errors

5. **Document**
   - Note what was broken
   - Note what fixed it
   - Update documentation

---

## Pro Tips

1. **Use `python3 -m json.tool`** to pretty-print JSON responses
2. **Use `head` and `tail`** to avoid overwhelming output
3. **Use `grep -n`** to get line numbers in search results
4. **Use `2>/dev/null`** to suppress error messages you don't need
5. **Keep terminals organized** - one for frontend, one for backend, one for commands
6. **Use `curl -s`** (silent) to avoid progress meters in output
7. **Pipe to `less`** for long output: `curl ... | less`
8. **Use `&&` to chain commands** that depend on each other
9. **Background processes** with `&` but monitor them with `jobs`
10. **Always check both backend AND frontend** - issues can be on either side

---

## Created: 2025-11-07
## Last Updated: 2025-11-07
## Author: Claude Code Investigation Session
