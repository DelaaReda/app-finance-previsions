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
0. **Poser une matrice d'hypothèses (avant patch)**
   - Lister au moins 3 causes candidates.
   - Pour chaque cause: 1 test d'invalidation court (commande + sortie attendue).
   - Interdit de patcher tant que la cause candidate #1 n'est pas prouvée.
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

## Priorisation sévérité (obligatoire)
- `P0`: bloque livraison/rôle/runtime (batch fermé à tort, claim impossible, boucle crash/timeout, guard hard-block).
- `P1`: dégrade fortement la fiabilité/perf mais contournable.
- `P2`: dette opérationnelle ou bruit non bloquant.
- Ordre d'exécution: `P0 -> P1 -> P2` (pas d'optimisation P2 tant qu'un P0 reste ouvert).

## Triangulation minimale (anti-fausse cause)
Toujours recouper au moins 3 sources:
- `queue/workboard` (état logique),
- `role-runner/events` (état exécution),
- `health/monitor` (état système).
Un seul signal ne suffit pas pour conclure.

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

## Template de clôture "complex issue" (inspiré terrain)
1. `N problèmes -> N fixes` (mapping explicite).
2. Pour chaque fix: commande de preuve + résultat observé.
3. Ligne d'état final obligatoire:
   - `health=<...>`
   - `blocked_roles=<...>`
   - `ready_tasks=<...>`

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
