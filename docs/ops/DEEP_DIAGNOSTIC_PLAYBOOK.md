# DEEP_DIAGNOSTIC_PLAYBOOK

Objectif: traiter vite les bugs complexes sans tourner en boucle, avec preuve causale complète.
Standard obligatoire pour tous les rôles agents (planner/dev/admin + spécialistes) dès qu'un incident complexe est détecté.

## Déclencheurs obligatoires
- Même blocker sur `>=2` ticks.
- `task_update=none_no_signal` répété alors qu'un item `READY` existe.
- Écart runtime visible (`monitor`/`health`) non expliqué par le contrat.
- Incohérence queue/workboard/sessions (`READY` mais claim impossible, batch fermé trop tôt, session engine incohérent).
- Mix d'engines sur une même lane (`codex` + `qwen`) dans `role-runner/*.events.log`.

## Méthode Deep standard (ordre strict)
1. **Isoler cause racine vs bruit**
   - Capturer l'erreur précise: `rc`, stacktrace, process exact, timestamp.
   - Séparer symptôme final et source réelle.
2. **Prouver le lien causal**
   - Établir `symptôme -> cause -> impact`.
   - Inclure preuves runtime quand pertinent: `PID/PPID`, locks, sessions tmux, état cron.
   - Vérifier explicitement:
     - schema queue (`items[]` canonique, pas `batches[]`)
     - engine unique par rôle (`MIXED_ENGINES` interdit en production)
     - fallback causes (`rc=124`, `timeout missing`, `Broken pipe`, `tmux no server`)
3. **Appliquer un fix chirurgical**
   - Scope minimal, ciblé sur la cause racine.
   - Interdit: patch volumineux exploratoire.
4. **Valider avec métriques avant/après**
   - Mesure factuelle avant et après (ex: RSS, codes retour, latence, compte d'erreurs).
   - Exécuter au moins un test ciblé.
5. **Vérifier l'absence de régression runtime**
   - Contrôler `cron/session/health` après correction.
   - Vérifier que la correction n'a pas cassé les lanes actives.

## Commandes minimales recommandées
- `bash scripts/agent_deep_troubleshoot.sh <role>`
- `python3 platform/automation/parallel_workstream.py context --role <role> --limit 5`
- `python3 platform/automation/parallel_workstream.py status --role <role> --compact`
- `bash scripts/fc_health_check.sh`
- `bash scripts/monitor_agents.sh`

Lecture rapide de `agent_deep_troubleshoot.sh`:
- `queue_schema`: détecte dérive `items[]` vs `batches[]`.
- `planner_guardian_recent`: détecte `HANDOFF_TO_MISSING` / `PLANNER_BATCH_ID_INVALID`.
- `runner_health`: détecte `MIXED_ENGINES` + causes fallback (`timeout_missing`, `Broken pipe`, `rc=124`).

## Contrat de sortie attendu
- `root_cause=<symptome->cause->impact>`
- `fix_applied=<patch_minimal>`
- `verify=<before:...; after:...; test:...>`
- `run_note` en mini paragraphe clair (>=5 mots).

## Phrase opérationnelle à réutiliser (copier-coller autorisé)
- isoler cause racine vs bruit (rc/stack/proc exact)
- prouver le lien causal (PID/PPID/locks/sessions)
- appliquer fix chirurgical (scope minimal)
- valider avec métriques avant/après
- vérifier absence de régression runtime (cron/session/health)

## Anti-patterns interdits
- Patch volumineux sans causal chain.
- "Fix" de contournement sans correction source.
- Blocage déclaré sans preuve runtime fraîche du tick courant.
- Multiplication de commandes exploratoires non reliées au problème.
