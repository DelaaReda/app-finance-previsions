# Guide des Outils Agents — Finance Copilot
_Source de vérité pour tous les agents. À lire avant de coder._
_Mis à jour: 2026-03-01 par admin-claude_

---

## 🏗️ Architecture du système

```
Cron (système)
  → fc_agent_tick.sh <role>
    → cron_tmux_role_runner.sh <role>
      → envoie le prompt au tmux session codex_<role>_cron
      → capture la réponse
      → écrit dans memory/agents/<role>.md
```

**Les 4 rôles actifs** (seuls ceux-ci ont des crons):
| Rôle | Session tmux | Cron | Peut éditer fichiers |
|------|-------------|------|---------------------|
| `planner` | `codex_planner_cron` | */15min | ✅ |
| `backend_engineer` | `codex_backend_engineer_cron` | */20min | ✅ |
| `frontend_engineer` | `codex_frontend_engineer_cron` | */20min (offset 7) | ✅ |
| `data_analyst` | `codex_data_analyst_cron` | */30min (offset 12) | ✅ |

---

## 🌐 OpenClaw Browser — Tester l'interface

L'agent peut utiliser le navigateur OpenClaw pour valider l'UI publique. Depuis 2026-04-16, viser EC2 public et non les listeners VM.

### Commandes essentielles

```bash
# Naviguer vers l'app
openclaw browser navigate "http://3.98.20.77/"

# Prendre un screenshot
openclaw browser screenshot
# → Enregistre dans ~/.openclaw/media/browser/<uuid>.jpg

# Lire les erreurs JS
openclaw browser errors

# Lire la console (logs API, etc.)
openclaw browser console

# Évaluer du JavaScript
openclaw browser evaluate "document.querySelectorAll('.news-card').length"

# Snapshot de la page (éléments interactifs)
openclaw browser snapshot
```

### Validation UI rapide (copier-coller)

```bash
# 1. Naviguer
openclaw browser navigate "http://3.98.20.77/"
sleep 3

# 2. Vérifier données live chargées
openclaw browser console | grep -E "API.*✅|news loaded|forecasts loaded"

# 3. Compter les news cards
openclaw browser evaluate "document.querySelectorAll('.news-card').length"

# 4. Vérifier badge LIVE
openclaw browser evaluate "!!document.getElementById('live-badge')"

# 5. Vérifier erreurs JS
openclaw browser errors
```

### Status du browser

```bash
openclaw browser status
# → enabled: true / running: true / cdpPort: 18800
```

---

## 🔧 API Backend — Endpoints disponibles

Base URL: `http://3.98.20.77/api`

```bash
# Santé
curl http://3.98.20.77/api/health | jq .

# News (460+ articles réels)
curl "http://3.98.20.77/api/news/feed?limit=5" | jq '.data.items[0].title'

# Forecasts (20 tickers)
curl "http://3.98.20.77/api/forecasts?limit=5" | jq '.data.rows[] | {ticker, direction, confidence}'

# Stocks avec historique prix
curl http://3.98.20.77/api/stocks/prices | jq '.data.tickers | keys'

# Top stocks
curl http://3.98.20.77/api/stocks/top | jq '.data.stocks[0]'

# Backtests
curl http://3.98.20.77/api/backtests | jq '.data.overall_metrics'

# Brief hebdo
curl http://3.98.20.77/api/brief/weekly | jq '.data | {title, sentiment}'

# Copilot Q&A
curl -X POST http://3.98.20.77/api/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Should I buy gold today?","tickers":["GLD"]}' | jq '.data.answer'
```

---

## 📁 Structure des fichiers importants

```
apps/
  api/src/                    # Backend Python (FastAPI)
    platform/main.py          # Entry point API
    platform/legacy/jobs/
      forecasts_simple.py     # ← Modèle forecast momentum (confidence 50-55%)
    domains/forecasts/        # Service forecasts
  web/src/                    # Frontend
    domains/forecasts/pages/
      index.html              # Page principale
      app.js                  # App V16 Diamond Nav
    contracts/
      apiConnector.js         # ← Bridge API↔UI (données live)
    platform/
      style.css               # CSS principal
      design-tokens.css       # Variables CSS

memory/agents/                # Mémoire persistante des agents
  planner.md
  frontend_engineer.md
  backend_engineer.md
  data_analyst.md

docs/
  product/planning/
    PRODUCT_VISION.md         # ← LIRE EN PREMIER (vision complète)
    WORKSTATE.md              # ← État actuel + protocoles planner
  orchestrator-ops/
    priority-queue.json       # Batches BATCH-03..07
  ops/
    ADMIN_ARCHIVE_TEAM_CHAT.md        # Canal de communication inter-agents
    REFERENCE_AGENT_TOOLS_GUIDE.md      # ← CE FICHIER
```

---

## 🩺 Scripts de maintenance

```bash
# Vérifier l'état complet du système
bash scripts/fc_health_check.sh

# Installer/réinstaller les crons
bash scripts/fc_setup_crons.sh

# Forcer un tick manuel d'un agent
bash scripts/fc_agent_tick.sh planner
bash scripts/fc_agent_tick.sh backend_engineer

# Recovery après réveil VM
bash scripts/fc_vm_resume.sh

# Voir les logs d'un agent
tail -50 logs-codex-runs/fc-ticks/planner.tick.log
tail -50 logs-codex-runs/fc-ticks/backend_engineer.tick.log

# Voir les sessions tmux actives
tmux ls

# Attacher à une session pour déboguer
tmux attach -t codex_planner_cron
# (Ctrl+B, D pour détacher)
```

---

## ⚠️ Problèmes connus et solutions

### Rate limit (Qwen ou Codex)
```bash
# Symptôme: "API rate limit reached" dans les logs
# Solution: Attendre ~10min, le cache se nettoie seul
# Ou: rm -f /home/venom/.openclaw/cron/role-state/*.rate_limit* 2>/dev/null
```

### Session tmux bloquée sur "Press Enter" (rate limit dialog)
```bash
# Symptôme: agent stuck, ne répond plus
# Solution: tuer la session, elle sera recréée au prochain tick
tmux kill-session -t codex_planner_cron
```

### VM vient de se réveiller (sleep/hibernation)
```bash
# Symptôme: crons n'ont pas tourné depuis >5min
# Solution automatique: fc_vm_resume.sh tourne toutes les 2min
# Solution manuelle:
bash scripts/fc_vm_resume.sh
```

### Backend arrêté
```bash
# Vérifier:
curl http://3.98.20.77/api/health

# Redémarrer (chercher le process):
ps aux | grep "run_api\|uvicorn\|gunicorn" | grep -v grep
# Puis relancer depuis la session tmux ou:
cd apps/api/src && python3 platform/main.py &
```

---

## 📋 Priorités BATCH-03 → BATCH-07

Voir `docs/product/planning/PRODUCT_VISION.md` pour la vision complète.

| Batch | Objectif | Status |
|-------|----------|--------|
| BATCH-03 | Frontend live + qualité données | 🔄 IN_PROGRESS |
| BATCH-04 | Brief quotidien + secteurs réels | 📋 PLANNED |
| BATCH-05 | Copilot "que faire aujourd'hui ?" | 📋 PLANNED |
| BATCH-06 | Forecasts multi-assets + judge IA | 📋 PLANNED |
| BATCH-07 | Deep dive asset + news intelligence | 📋 PLANNED |

### BATCH-03 success criteria (vérifiables)
```bash
# 1. News live dans l'UI
openclaw browser evaluate "window.newsItems && window.newsItems[0].headline" 

# 2. Forecasts avec confiance > 0
curl http://3.98.20.77/api/forecasts?limit=1 | jq '.data.rows[0].confidence'
# → doit être > 0.55 pour être utile

# 3. Stocks avec vrais % de changement
curl http://3.98.20.77/api/stocks/top | jq '.data.stocks[0].change_percent'
# → doit être != 0.0

# 4. Backend fix: change_percent dans /api/stocks/top
# Fichier: apps/api/src/platform/main.py ou le service stocks
# Problème: change_percent=0.0 car pas calculé depuis l'historique
```
