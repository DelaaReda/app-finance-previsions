# 🛠️ DEV TOOLS GUIDE — Finance Copilot Agents

Guide de référence pour tous les outils disponibles dans le workspace.
Chaque commande a été **testée et validée** sur cette VM (2026-03-01).

---

## 1. Browser Automation (openclaw browser)

Le browser Chromium est toujours actif (CDP port 18800). Utilise-le pour valider l'UI, tester des flux, capturer des preuves.

### Workflow type QA/Frontend

```bash
# 1. Naviguer vers l'app
openclaw browser navigate "http://localhost:5173/"

# 2. Attendre le chargement complet
openclaw browser wait --load domcontentloaded

# 3. Snapshot d'accessibilité (liste tous les éléments interactifs avec ref=)
openclaw browser snapshot --labels

# 4. Screenshot (sauvegardé dans ~/.openclaw/media/browser/)
openclaw browser screenshot
# → retourne: MEDIA:~/.openclaw/media/browser/<uuid>.jpg

# 5. Lire les logs console (succès API, erreurs JS)
openclaw browser console

# 6. Vérifier les erreurs JS
openclaw browser errors

# 7. Inspecter les requêtes réseau
openclaw browser requests
```

### Actions interactives

```bash
# Cliquer sur un bouton (utiliser ref= du snapshot)
openclaw browser click --ref e1

# Remplir un champ
openclaw browser fill --ref e42 --value "NVDA"

# Évaluer du JS dans la page
openclaw browser evaluate --expression "window.newsItems?.length"
openclaw browser evaluate --expression "window.liveForecasts?.length"
openclaw browser evaluate --expression "document.querySelector('.live-badge')?.textContent"

# Attendre un sélecteur CSS
openclaw browser wait --selector ".news-item" --timeout 5000
```

### Exemples de preuve browser (pour EVIDENCE dans ta sortie)

```bash
# Preuve: API live data chargée
openclaw browser console | grep "\[API\]"
# → [LOG] [API] ✅ 20 news loaded
# → [LOG] [API] ✅ 5 stocks, top movers: GOOGL (+83.04% 30d)

# Preuve: Pas d'erreurs JS
openclaw browser errors
# → doit retourner 0 erreurs (ou seulement "appData is not defined" qui est bénin)
```

---

## 2. API Backend (curl)

Backend disponible sur `http://localhost:8050`

### Endpoints principaux

```bash
# Health check
curl -s "http://localhost:8050/api/health" | python3 -m json.tool

# News (460+ articles)
curl -s "http://localhost:8050/api/news/feed?limit=5" | python3 -m json.tool

# Forecasts (20 prédictions)
curl -s "http://localhost:8050/api/forecasts?limit=5" | python3 -m json.tool

# Prix actions avec historique
curl -s "http://localhost:8050/api/stocks/prices" | python3 -m json.tool

# KPIs dashboard
curl -s "http://localhost:8050/api/dashboard/kpis" | python3 -m json.tool

# Backtests
curl -s "http://localhost:8050/api/backtests" | python3 -m json.tool

# Judge AI (multi-model)
curl -s "http://localhost:8050/api/judge" | python3 -m json.tool

# Top movers (bug connu: change_percent=0.0 — utiliser /api/stocks/prices à la place)
curl -s "http://localhost:8050/api/stocks/top" | python3 -m json.tool
```

### Vérifications clés

```bash
# Vérifier qualité données forecasts
curl -s "http://localhost:8050/api/forecasts?limit=20" | python3 -c "
import sys, json
data = json.load(sys.stdin)
forecasts = data.get('forecasts', [])
high_conf = [f for f in forecasts if f.get('confidence',0) > 0.65]
print(f'Total: {len(forecasts)}, High confidence (>65%): {len(high_conf)}')
for f in high_conf[:3]:
    print(f'  {f[\"ticker\"]}: {f[\"confidence\"]*100:.0f}% {f[\"direction\"]}')
"

# Vérifier change_percent réels
curl -s "http://localhost:8050/api/stocks/prices" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for ticker, info in data.get('prices',{}).items():
    pts = info.get('points',[])
    if len(pts) >= 2:
        chg = (pts[-1]['close'] - pts[0]['close']) / pts[0]['close'] * 100
        print(f'{ticker}: {pts[-1][\"close\"]:.2f} ({chg:+.1f}% 30d)')
"
```

---

## 3. Git Workflow

```bash
# Voir ce qui est modifié
git status
git diff --stat

# Commit livraison (TOUJOURS inclure le role dans le message)
git add -A
git commit -m "feat(frontend): connect forecasts widget to live API [frontend_engineer]"

# Voir l'historique récent
git log --oneline -10
```

---

## 4. Tmux — Sessions actives

```bash
# Lister toutes les sessions
tmux ls

# Se connecter à une session
tmux attach -t codex_planner_cron

# Voir le dernier output sans s'attacher
tmux capture-pane -pt codex_planner_cron -S -20

# Tuer une session zombie
tmux kill-session -t nom_session
```

---

## 5. Health Check Global

```bash
# Dashboard santé complet (snapshot)
bash scripts/agent_health.sh

# Dashboard en temps réel (rafraîchi toutes les 15s)
bash scripts/agent_health.sh --watch

# Nettoyage après réveil VM
bash scripts/vm_wake_cleanup.sh

# Forcer le nettoyage
bash scripts/vm_wake_cleanup.sh --force
```

---

## 6. Frontend Files

```
apps/web/src/domains/forecasts/pages/
├── index.html          ← HTML principal (servi sur :5173)
├── app.js              ← Logique UI, window globals, renderNewsFeed()
├── mockData.js         ← Données fallback (remplacées par API live)
└── ../contracts/
    └── apiConnector.js ← Bridge API→window globals (modifié le 2026-02-28)
        └── populateWindowGlobals() → window.newsItems, window.liveForecasts, etc.

apps/web/src/domains/forecasts/platform/
├── style.css           ← Styles principaux
└── design-tokens.css   ← Variables CSS
```

### Variables window globales (peuplées par apiConnector.js)

```javascript
window.newsItems      // [{headline, impact, effect, time, source, category}]
window.liveForecasts  // [{ticker, direction, confidence, horizon, reasoning}]
window.topMovers      // [{ticker, price, change, changePercent30d, direction}]
window.liveStocks     // {SPY: {price, change30d}, ...}
```

---

## 7. Logs & Debug

```bash
# Logs backend
tail -50 logs/backend.log 2>/dev/null || journalctl --user -u finance-backend -n 50

# Logs frontend
tail -20 logs/frontend.log 2>/dev/null

# Logs ticks agents
tail -30 logs-codex-runs/fc-ticks/planner.cron.log
tail -30 logs-codex-runs/fc-ticks/backend_engineer.cron.log

# Logs VM wake
tail -20 logs-codex-runs/vm-wake.log

# Processus actifs
ps aux | grep -E "python3.*main|http.server" | grep -v grep
```

---

## 8. Workboard & Tâches

```bash
# Lire le workboard
cat docs/orchestrator-ops/priority-queue.json | python3 -m json.tool

# Lire ta mémoire de rôle
cat memory/agents/<ton_role>.md | tail -50

# Lire le product vision
cat docs/product/planning/PRODUCT_VISION.md

# Lire le workstate (batch courant)
cat docs/product/planning/WORKSTATE.md
```

---

## 9. Checklist de livraison

Avant de marquer une tâche DONE, vérifier :

- [ ] `git log --oneline -3` montre ton commit
- [ ] `openclaw browser errors` → 0 erreurs critiques
- [ ] `openclaw browser console | grep "\[API\]"` → data live confirmée
- [ ] `curl http://localhost:8050/api/health` → HTTP 200
- [ ] `curl http://localhost:5173/` → HTTP 200

