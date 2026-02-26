# Orchestrator Ops — Improvements

## Changelog
- Initialized.

## 2026-02-24 22:55 ET — Backlog d’amélioration (classé ROI)

### ROI-1 (Très élevé) — Aligner états queue ↔ préflight (Stop-the-line)
- **Problème:** état `IN_SPRINT` non accepté par le validateur preflight pour `BATCH-01`.
- **Action:** normaliser le mapping d’états autorisés (queue + script `preflight_dispatch.sh`) et ajouter un test de contrat d’états.
- **Owner role (Scrum):** Scrum Master + Dev
- **Impact:** débloque immédiatement le flux et réduit blocages récurrents.
- **Effort:** S
- **Risk:** faible (changement local de validation)
- **Rollback:** restaurer mapping précédent via git checkout du script/JSON.

### ROI-2 (Élevé) — Gate de complétude DoD avant clôture
- **Problème:** sorties non exploitables malgré déclarations GO; artefacts PASS manquants.
- **Action:** gate automatique `proof-completeness` exigeant: `DELTA,EVIDENCE,RISKS,NEXT,VERDICT,BLOCKER_ID,NEXT_ACTION_UNIQUE` + `VERDICT:PASS` + `BLOCKER_ID:NONE`.
- **Owner role (Scrum):** QA + Tester
- **Impact:** élimine faux DONE et réduit carry-over caché.
- **Effort:** M
- **Risk:** moyen (plus de rejets initiaux)
- **Rollback:** exécuter gate en mode warn-only pendant 1 sprint.

### ROI-3 (Élevé) — Réduction bruit LLM (token/latence)
- **Problème:** 23 warnings, 8 réponses trop longues, boucles de reformulation.
- **Action:** budgets de longueur stricts par rôle (Planner/Architect/DeliveryManager), hard-truncate + template réponse court obligatoire.
- **Owner role (Scrum):** Architect + Manager
- **Impact:** cycle-time réduit, meilleure lisibilité, moins de rate-limit.
- **Effort:** S
- **Risk:** moyen (perte de contexte si trop agressif)
- **Rollback:** relever plafonds par rôle de +30%.

### ROI-4 (Moyen+) — Assainir env cross-platform orchestrator
- **Problème:** `project_dir` macOS dans run.json sur VM Linux.
- **Action:** résolution dynamique du workspace (cwd) + preflight “path sanity”.
- **Owner role (Scrum):** DevOps/Dev
- **Impact:** supprime une classe entière de blocages d’initialisation.
- **Effort:** S
- **Risk:** faible
- **Rollback:** fallback explicite via variable d’environnement forcée.

### ROI-5 (Moyen) — WIP limit Scrum pour P0
- **Problème:** 3 P0 en parallèle avec 0 DONE.
- **Action:** limiter WIP P0 à 2 max; pas de démarrage story suivante sans fermeture d’un blocker structurel.
- **Owner role (Scrum):** Product Owner + Scrum Master
- **Impact:** meilleure probabilité de finish intra-sprint.
- **Effort:** S (process)
- **Risk:** faible
- **Rollback:** revenir au WIP actuel si under-utilization >2 jours.

## 2026-02-25 18:30 ET — Améliorations globales (issues du mode séquentiel)

### Constat runtime (sur runs séquentiels planner/dev/tester/qa)
- Les runs finissent `ok` avec latence contenue (~56s à ~75s).
- Le chemin réel est stable mais dégradé: `tmux primary -> timeout/stall-abort`, `tmux retry -> timeout/stall-abort`, puis `codex_fallback -> success`.
- Le fallback est donc le chemin nominal de fait; le scraping tmux n’apporte presque pas de valeur décisionnelle.

### ROI-1 (Très élevé) — Passer en `codex_exec` primary, tmux en secours
- **Problème:** dépendance forte au scraping d’écran tmux, fragile et coûteuse en temps.
- **Action:** basculer le runner en mode primary `codex_exec` (thread/session persistants), et garder tmux seulement comme canal de repli/observabilité.
- **Owner:** Dev + Architect
- **Impact:** réduction des timeouts inutiles et de la variabilité de run.
- **Effort:** M
- **Risk:** moyen (gestion d’état session codex_exec).
- **Rollback:** feature-flag `TMUX_ROLE_RETRY_ENGINE_DEFAULT=tmux`.

### ROI-2 (Très élevé) — Déclarer explicitement un mode d’orchestration (`sequential` vs `parallel`)
- **Problème:** changement manuel des jobs actifs, source d’erreur humaine.
- **Action:** ajouter un script de pilotage unique (ex: `scripts/set_orchestration_mode.sh`) qui applique un profil:
  - `sequential`: 1 rôle actif + 2 admins,
  - `parallel`: tous les rôles actifs.
- **Owner:** DevOps/Dev
- **Impact:** opérations reproductibles et auditables.
- **Effort:** S
- **Risk:** faible
- **Rollback:** commande directe `openclaw cron edit --enable/--disable`.

### ROI-3 (Élevé) — Rendre les logs runner 100% structurés (JSONL)
- **Problème:** diagnostics encore semi-textuels, parsing fragile.
- **Action:** écrire chaque événement runner en JSONL (`event`, `role`, `tick`, `rc`, `duration_ms`, `source`, `fallback_used`, `stall_abort_count`).
- **Owner:** Dev
- **Impact:** tableaux de bord fiables + comparaisons automatiques par rôle.
- **Effort:** M
- **Risk:** faible
- **Rollback:** conserver écriture texte en parallèle pendant transition.

### ROI-4 (Élevé) — SLO et alerting par rôle
- **Problème:** pas de seuil explicite "bonne exécution" vs "dégradation".
- **Action:** définir SLO minimaux (ex: `duration<90s`, `errors=0`, `fallback_rate<80%` cible progressive) avec alerte si violation N fois de suite.
- **Owner:** ClawSentinel + AdminApp
- **Impact:** pilotage qualité orienté résultats, pas uniquement statut `ok`.
- **Effort:** M
- **Risk:** faible
- **Rollback:** passer alerting en mode `warn-only`.

### ROI-5 (Moyen+) — Réduire le coût de la double tentative tmux
- **Problème:** primary+retry tmux prennent du temps alors que le fallback réussit déjà.
- **Action:** profil adaptatif:
  - si `stall-abort` répété, réduire `PROMPT_TIMEOUT_SECONDS`/`RETRY_PROMPT_TIMEOUT_SECONDS`,
  - déclencher fallback plus tôt.
- **Owner:** Dev
- **Impact:** baisse immédiate de latence et de contention.
- **Effort:** S
- **Risk:** faible
- **Rollback:** restaurer timeouts statiques actuels.

## 2026-02-25 19:30 ET — Validation séquentielle post-correctifs

### Changements appliqués
- `cron_tmux_role_runner.sh`:
  - retry prompt rendu strictement role-aware (artefact requis par rôle dans `EVIDENCE`);
  - `TMUX_ROLE_CODEX_EXEC_RESUME` ajouté (par défaut `0`) pour éviter la contamination inter-runs;
  - durcissement de la sortie fallback/réessai sous contrat 8 clés + contrôle de spécificité.
- `configure_tmux_role_crons.sh`:
  - profil cron rôle basculé sur `TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk`,
  - `TMUX_ROLE_STALL_ABORT_SECONDS=0`,
  - propagation explicite `TMUX_ROLE_CODEX_EXEC_RESUME=0`.
- ajout du script opératoire `scripts/validate_roles_sequential.sh` (activation/force-run/désactivation rôle par rôle).

### Résultat mesuré (séquentiel 1 rôle actif à la fois)
- 8/8 rôles validés (`planner -> dev -> tester -> qa -> architect -> po -> scrum_master -> clawsentinel`).
- Tous les rôles livrent un artefact spécifique (`planner_artifact`, `dev_artifact`, etc.).
- Aucun rôle en `BLOCKED` sur la séquence.
- Latence observée: ~31s à ~70s selon rôle.
- État final runtime: seuls les jobs admin restent actifs (rôles désactivés).

### Points encore à traiter
- Le canal tmux interactif reste non fiable pour soumission clavier automatisée (input visible, réponse absente); l’exécution fiable est désormais `codex_exec`.
- Industrialiser une gate “stop-on-failure” automatique sur la chaîne séquentielle (arrêt immédiat si `ROLE_CONTRACT_MISSING`).

## 2026-02-25 20:50 ET — Industrialisation validation séquentielle

### Implémenté
- `scripts/validate_roles_sequential.sh` renforcé:
  - `stop-on-failure` par défaut (arrêt immédiat si gate KO),
  - règles de gate: artefact requis par rôle, blocker clair, pas de `ROLE_CONTRACT_MISSING`, pas de `STATUS/VERDICT=BLOCKED`,
  - génération d’un rapport JSONL (`logs-codex-runs/role-runner/sequential-validate-*.jsonl`),
  - options: `--roles`, `--timeout-ms`, `--report-file`, `--continue-on-failure`.
- nouveau script de pilotage:
  - `scripts/set_orchestration_mode.sh`
  - modes: `admins-only`, `sequential --role <role>`, `parallel`, `--dry-run`.
- trace runner clarifiée:
  - `startup_mode=codex_exec_fresh` quand `TMUX_ROLE_CODEX_EXEC_RESUME=0`.

### Validation exécutée
- Sweep complet `8/8` rôles, mode séquentiel strict, gate `OK` partout.
- Rapport: `logs-codex-runs/role-runner/sequential-validate-20260225T203915Z.jsonl`.
- Statistiques run:
  - `total=8`, `gate_ok=8`, `failed=0`,
  - `avg_duration_ms=49707.75`,
  - `avg_tokens=15995.25`.

### Décision opérationnelle
- Maintenir `admins-only` entre les sessions de troubleshooting.
- Activer les rôles uniquement via `set_orchestration_mode.sh` pour éviter les dérives manuelles.

## 2026-02-25 21:20 ET — Strict chain readiness (core flow)

### Implémenté
- `scripts/validate_roles_sequential.sh`:
  - ajout `--strict-ready-chain` (chaîne `planner -> dev -> tester -> qa`),
  - ajout `--chain-target BATCH-<n>` pour forcer la cible attendue,
  - ajout `--no-summary`,
  - correction parsing `--roles` (newline-safe),
  - extraction `BATCH-*` stabilisée (première occurrence priorisant `NEXT_ACTION`),
  - nettoyage `\r` sur extraction des champs (évite faux `BLOCKER_NOT_CLEAR`).
- En mode strict, le validateur échoue immédiatement si:
  - target de chaîne absente,
  - target incohérente entre rôles,
  - artefact rôle absent,
  - blocker non clear,
  - output non conforme/blocked.

### Tests exécutés
- Cas négatif validé:
  - `--strict-ready-chain --roles dev,tester,qa` sans planner/target => exit `2` attendu.
- Cas strict core validé:
  - `--strict-ready-chain --roles planner,dev,tester,qa` => `gate_ok=4/4`, `failed=0`.
  - report: `logs-codex-runs/role-runner/sequential-validate-20260225T211519Z.jsonl`.
- État final runtime confirmé: `admins-only`.
