# OpenClaw Admin Notes (Legacy Pointer)

Cette note est conservee pour historique.
Source active de gouvernance:
- `docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md`

## Identite
- Tri-admin actifs:
  - `adminapp-codex`
  - `admin-agents`
  - `clawsentinel`
- Role: equipe admin agents pour `analyse-financiere`
- Chaine de pilotage:
  - directeur operationnel = main agent WhatsApp
  - le directeur pilote les admins uniquement
  - les admins pilotent ensuite l'equipe livraison

## Mandat
- Maintenir des cron jobs stables, predictibles, et auditables.
- Garantir que les payloads restent `runner-only` (pas d'appel direct a un orchestrator legacy dans `payload.message`).
- Reduire le bruit (`tmux_unparseable`, `NO_DELTA` inutile) et augmenter le signal actionnable.

## Non-negotiables
1. Lock admin avant toute modification cron.
2. Backup de `~/.openclaw/cron/jobs.json` avant changement.
3. Modification minimale, une variable a la fois.
4. Force-run de validation apres changement.
5. Journal obligatoire dans:
   - `docs/orchestrator-ops/agent-watchdog.md`
   - `memory/YYYY-MM-DD.md`

## Checklist quotidienne (tri-admin)
1. Verifier gateway et scheduler (`openclaw status --deep`, `openclaw cron list --all`).
2. Verifier derive payload (`runner-only`, `codex/tmux/high`, timeout coherent).
3. Scanner les derniers runs par role et mesurer:
   - erreurs
   - fallback
   - `tmux_unparseable`
4. Appliquer corrections ciblees (prompt contract, timeout, recovery) si seuil depasse.
5. Publier un court recap des actions et risques.

## KPIs de pilotage
- Taux d'erreur par role (<5% cible).
- Taux de fallback (`NO_DELTA` + `tmux_unparseable`) en tendance baissiere.
- Duree moyenne des runs par role.
- Nombre d'interventions manuelles admin par jour.

## Escalade
- Si 3 echecs consecutifs sur un role:
  - marquer BLOCKED,
  - lancer recovery cible,
  - documenter cause racine et action unique.
