# ORCHESTRATION LEAN — Guide Équipe 3 Rôles
## Mis à jour: 2026-03-03 (topologie canonique planner/dev/admin)

---

## Mise à jour critique cron (2026-03-03)

Problème observé: dérive de crontab entre anciennes lanes (`backend_engineer/frontend_engineer/data_analyst`) et topologie canonique lean.
Impact: monitoring confus, signaux contradictoires, et perte de cadence delivery.

Cadence minimale à garantir dans le crontab actif:
- `planner`: `:00/:22/:44`
- `dev`: `:06/:28/:50`
- `admin`: `:12/:34/:56`

Commandes de vérification:
```bash
crontab -l
bash scripts/monitor_agents.sh
bash scripts/fc_health_check.sh
```

Notes:
- Les lignes cron legacy (`backend_engineer`, `frontend_engineer`, `data_analyst`, etc.) doivent être supprimées.
- Si une ligne legacy subsiste, `fc_agent_tick.sh` la redirige, mais c'est un mode de compatibilité temporaire.
- Le cleanup historique des logs est géré par `scripts/cleanup_monitoring_noise.sh` (cron toutes les 4h, minute 17).
- Les tâches `BATCH-07-*` doivent rester `WAITING_DEP` tant que `BATCH-06` n'est pas clos (pas de READY côte-à-côte).

---

## Architecture simplifiée

```
AVANT (10 rôles)                    APRÈS (3 rôles)
─────────────────────────────────   ─────────────────────
planner                         →   planner
architect + po + scrum_master   →   planner
analyst                         →   planner
─────────────────────────────────
backend_engineer                →   dev
frontend_engineer               →   dev
data_analyst                    →   dev
integrator                      →   dev
tester                          →   dev
─────────────────────────────────
clawsentinel                    →   admin
infra_engineer                  →   admin
qa                              →   admin
```

**Résultat:** 70% de réduction des appels Codex. Quota préservé pour le vrai travail.

---

## Les 3 rôles

### `dev` — Le builder (cadence: voir crontab active)
**Fait:** code backend, code frontend, pipeline données, tests, self-QA
**Fichiers:** `apps/`, `scripts/` (non-ops)
**Mémoire:** `memory/agents/dev.md`
**Session tmux:** `codex_dev_cron`

### `planner` — La vision (cadence: voir crontab active)
**Fait:** specs, déblocage, ouvrir/fermer batches, roadmap
**Ne fait PAS:** code, screenshots, preuves UI complexes
**Règle:** curl HTTP 200 = preuve suffisante pour clore un batch backend
**Mémoire:** `memory/agents/planner.md`
**Session tmux:** `codex_planner_cron`

### `admin` — L'ops (cadence: voir crontab active)
**Fait:** health checks, restart services, vider rate limits, tuer zombies
**Mémoire:** `memory/agents/admin.md`
**Session tmux:** `codex_admin_cron`

---

## Crontab (source de vérité runtime)

```
# Vérifier l'état réel:
crontab -l
bash scripts/monitor_agents.sh
```

Notes:
- Le monitor normalise les rôles techniques en lanes canoniques:
  - `backend_engineer`, `frontend_engineer`, `data_analyst`, etc. -> `dev`
  - `vision-architect-tasks-planner`, `analyst`, `architect`, etc. -> `planner`
  - `clawsentinel` -> `admin`
- Selon le profil actif, la lane `admin` peut être temporairement désactivée côté cron.

---

## Fallback Qwen (NE PAS MODIFIER)

- Codex rate-limité → qwen prend le relais automatiquement
- qwen rate-limité → skip propre du tick (pas de zombie)
- Les deux rate-limités → skip, reprend au prochain tick
- Cache rate-limit: 240s (4min) par défaut
- Admin vide les caches manuellement si nécessaire

---

## Forecasts v2 (multi-signal, 2026-03-02)

Nouveau moteur de confiance dans `forecasts_simple.py`:

| Signal | Poids | Source |
|--------|-------|--------|
| Momentum 1j | 50% | `change_1d` (last vs prev point) |
| Tendance 5j | 30% | `change_5d` (first vs last point) |
| Ratio jours haussiers | 20% | `up_days / total_days` |

Résultat: confidence 40-85% selon contexte marché (était 45-55% fixe).

---

## Comment lancer la migration

```bash
# Dans le workspace
cd /home/venom/analyse-financiere

# 1. Migrer les fichiers de workboard (si nécessaire)
python3 scripts/migrate_workboard_lean.py

# 2. Installer/reconcilier le crontab canonique
bash scripts/install_lean_crontab.sh

# 3. Vérifier
bash scripts/monitor_agents.sh
bash scripts/fc_health_check.sh
bash scripts/cleanup_monitoring_noise.sh
```

---

## Roadmap batches (état 2026-03-03)

| Batch | État | Rôle dev | Priorité |
|-------|------|----------|---------|
| BATCH-01/02/03/04 | ✅ DONE | - | - |
| BATCH-05 | 🔄 EN COURS | brief/daily + copilot/ask | P0 |
| BATCH-06 | 📋 READY | forecasts multi-assets + judge | P1 |
| BATCH-07 | ⏸ WAITING_DEP | deep dive + news intelligence | P1 |

---

## Problèmes courants

**"signal_unparseable" en boucle**
→ La mémoire du rôle est trop grande → réinitialiser avec `memory/agents/<role>.md`

**"READ_ONLY_TASK_UPDATE_INVALID"**
→ Le runner tourne en mode fallback → vérifier `allow_file_edits` dans cron-map

**"MENTOR_EVIDENCE_MISSING"**
→ Planner exige une preuve impossible à obtenir → curl HTTP 200 = preuve suffisante, configurer dans planner.md

**Rate limit les deux modèles**
→ `rm -f /home/venom/.openclaw/cron/role-state/*.rate_limit_gate_cache`

**Backend DOWN**
→ `bash finance-copilot.sh restart`
