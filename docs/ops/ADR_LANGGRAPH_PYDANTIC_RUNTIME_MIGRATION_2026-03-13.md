# ADR - Migration de la plomberie d'orchestration vers un runtime durable `LangGraph` + contrats typés

Date: 2026-03-13
Status: Accepted target / execution-ready
Owner: architecte agents + plomberie

See also:

- `docs/ops/CANONICAL_RUNTIME_MODE.md`

## Contexte

La plomberie actuelle a trois fragilités structurelles:

- la verite runtime reste dispersee entre `parallel-workstreams.json`, `priority-queue.json`, registres annexes, logs, JSONL et contrats texte
- le planner peut etre bloque par des projections docs corrompues ou des helpers Python fragiles
- les mutations critiques `dispatch -> collect -> merge -> proof -> complete` restent reparties entre bash, JSON et parseurs texte

Signaux observes dans le depot:

- `planner_orchestrator_bridge_failed` sur `BOARD_READ_ERROR` a deja bloque le planner pendant des heures
- `/api/status` et `doctor` restent couples a des imports et calculs trop lourds pour un endpoint de sante
- le shadow runtime existe deja sous `platform/automation/runtime/` et `platform/automation/planning/plane/`, mais il n'est pas encore la verite canonique

Contrainte non negociable:

- le model plane garde `codex exec` comme chemin principal
- `qwen cli` reste un fallback final du plane agent uniquement
- OpenClaw reste un plan operateur/session, pas une source de verite runtime
- aucun composant runtime ne doit introduire une dependance a un provider API externe comme source principale d'execution agent

## Decision

Nous terminons la migration vers un control-plane durable fonde sur:

- `LangGraph` pour l'orchestration planner durable et la reprise
- `Pydantic` comme base obligatoire de contrats types et validation
- `PydanticAI` comme couche optionnelle, utile pour outillage agent/retry/output discipline, mais non requise pour le coeur runtime
- `SQLite` locale comme event store canonique et stockage de graph state

Le model plane reste inchange:

- `ModelInvocationPort`
- implementation unique: `CodexCliAdapter`
- backend principal: `codex exec`
- fallback final agent: `qwen cli`
- support operateur/session: OpenClaw

## Pourquoi ce choix

`LangGraph` est retenu parce que le probleme principal du projet est la durabilite d'execution:

- checkpointing
- reprise apres crash
- idempotence des side effects
- transitions de graphe explicites
- separation nette entre logique de decision et projections de compatibilite

`Pydantic` est retenu comme fondation car le besoin central est la validation stricte des decisions planner, des resultats capability et des preuves de livraison.

`PydanticAI` n'est pas le coeur du plan. Il peut etre utilise comme surcouche la ou il apporte de la valeur, mais le runtime ne doit pas dependre de lui pour rester operationnel.

## Alternatives ecartees

### `openai-agents-python`

Rejete comme backbone principal.

Raison:

- bon SDK agent, handoffs, sessions et guardrails
- moins adapte comme verite runtime durable locale que `LangGraph`
- moins naturel dans un environnement ou le model plane ne parle pas a une API provider native

Conclusion:

- acceptable comme inspiration ou POC secondaire
- non retenu comme moteur d'orchestration principal

### `CrewAI` / `AutoGen`

Rejetes comme backbone principal.

Raison:

- plus centres collaboration/teams d'agents que verite runtime planner-only durable
- mismatch avec le besoin de graph checkpoints, projections deterministes et cutover progressif sur une plomberie existante

Conclusion:

- utiles pour experimentation produit
- non retenus comme source de verite runtime

### `Microsoft Agent Framework`

Rejete pour la cible immediate.

Raison:

- direction interessante sur workflows et durable execution
- trop loin du model plane actuel et du besoin de migration rapide sans requalifier tout le control plane

Conclusion:

- garder en POC secondaire uniquement

## Portee

### Inclus

- planner-only durable runtime
- store canonique SQLite pour graph state + events
- contrats typés pour decisions, resultats, checks et proofs
- projections JSON / JSONL de compatibilite
- bascule progressive de `/api/status`, `/api/doctor`, activity feed et indicateurs planner vers la nouvelle verite

### Exclu

- changement de model plane
- refonte frontend
- multi-scheduler par role
- remplacement complet immediate de tous les wrappers shell

## Principes d'architecture

1. Une seule source de verite runtime:
   `LangGraph state + SQLite event store`
2. Un seul scheduler actif:
   `planner`
3. Une seule porte d'appel modele:
   `ModelInvocationPort -> CodexCliAdapter`
4. Les projections JSON restent publiees pour compatibilite, mais ne bloquent jamais l'orchestration canonique.
5. Aucun parser texte n'est autorise comme source de verite de mutation.
6. Toute mutation board doit etre idempotente et rattachee a un `invocation_id` ou `idempotency_key`.

## Source de verite cible

### Canonique

- `orchestration-runtime.sqlite`
- `planner_graph_state`
- `orchestration_events`

### Secondaire / projection

- `logs-codex-runs/orchestrator-state/priority-queue.json`
- `logs-codex-runs/orchestrator-state/parallel-workstreams.json`
- `docs/operations/orchestrator/priority-queue.json`
- `docs/operations/orchestrator/parallel-workstreams.json`
- JSONL d'evenements pour shell/outillage

Regle dure:

- une projection corrompue ne doit jamais provoquer `BOARD_READ_ERROR` si le store canonique est sain

## Contrats obligatoires

Les modeles suivants deviennent la base canonique:

- `PlannerDecision`
- `CapabilityTask`
- `CapabilityResult`
- `DeliveryProof`
- `RuntimeCheck`
- `ScrumAdvice`
- `PlannerGraphState`
- `OrchestrationEvent`

Regles:

- toute mutation board exige un `CapabilityResult` valide
- tout `complete` exige une `DeliveryProof` valide
- le contrat texte 8 lignes ne devient qu'une projection legacy

## Interface du model plane

Le `ModelInvocationPort` doit couvrir au minimum:

- `start`
- `resume`
- `collect`
- `status`

Chaque invocation canonique doit aussi porter:

- `invocation_id`
- `idempotency_key`
- `backend_requested`
- `backend_used`
- `fallback_reason`
- `invocation_status`
- `heartbeat_ts`
- `provider_plane`

Note:

`status` est ajoute explicitement. `start/resume/collect` seuls ne suffisent pas pour raisonner proprement sur heartbeat, dispatch deja lance, reprise sure et non-duplication.

## Runtime planner cible

Noeuds minimaux du graphe:

- `load_runtime_truth`
- `reconcile_runtime_state`
- `select_actionable_task`
- `dispatch_capability`
- `wait_or_collect_result`
- `validate_contract_and_proof`
- `apply_workboard_mutation`
- `emit_events_and_monitor_projection`
- `close_or_requeue`

Invariants:

- aucun side effect externe dans les noeuds de selection
- tout side effect doit etre rejouable sans duplication
- `dispatch_capability` doit produire un `invocation_id` stable
- `apply_workboard_mutation` est la seule etape autorisee a muter les projections board/queue

## Strategie de migration

Le depot n'est pas un greenfield.

Le shadow runtime existe deja dans:

- `platform/automation/runtime/`
- `platform/automation/planning/plane/`

La strategie retenue est donc:

- terminer la migration
- ne pas recommencer une deuxieme architecture parallele

## Lots d'implementation

### Lot 0 - Stabilisation de lecture sante

Objectif:

- decoupler `/api/status` et `doctor` des imports fragiles et des helpers metier lourds

Travail:

- introduire un reader stable `runtime_truth_reader`
- faire lire l'etat planner/queue/workboard/event store depuis ce reader
- degrader proprement si un module metier annexe est casse

Gate de sortie:

- `/api/status` repond sans casser si un helper metier contient une erreur de syntaxe
- `fc_doctor` renvoie un JSON degrade explicite au lieu d'echouer brutalement

### Lot 1 - Model plane adapter canonique

Objectif:

- centraliser 100% des appels modele dans `CodexCliAdapter`

Travail:

- terminer l'extraction depuis `openclaw_control_plane.py` et `planner_subagent_manager.py`
- interdire les appels directs `codex exec` hors adapter
- imposer `invocation_id`, `status`, `started_at`, `last_heartbeat`, `backend`

Gate de sortie:

- tout dispatch/collect planner passe par le port unique
- aucune mutation runtime ne depend d'un parseur shell ad hoc

### Lot 2 - Contrats typés canoniques

Objectif:

- faire des modeles typés la seule entree acceptable pour decisions, resultats et proofs

Travail:

- rendre `Pydantic` obligatoire dans tout le chemin planner/subagents
- convertir `role_contract_guard.py` en validateur dual-mode:
  - entree canonique: JSON typé
  - projection compatibilite: texte 8 lignes

Gate de sortie:

- un resultat subagent invalide est rejete avant toute mutation
- le texte 8 lignes n'est plus qu'une sortie derivee

### Lot 3 - Event store canonique

Objectif:

- rendre SQLite la verite d'evenements et d'etat planner

Travail:

- completer `event_store.py`
- ecrire tous les dispatch, resultats, merges, blocks, retries, proofs dans SQLite
- garder les JSONL comme projections

Gate de sortie:

- activity feed et metrics planner peuvent se reconstruire depuis SQLite sans lire les logs bruts

### Lot 4 - Planner graph-led en shadow-write

Objectif:

- faire tourner le planner graph en ecriture d'ombre avant le cutover

Travail:

- sur chaque tick planner legacy:
  - ecrire `PlannerGraphState`
  - ecrire `OrchestrationEvent`
  - comparer les decisions shadow vs legacy

Gate de sortie:

- les decisions shadow sont equivalentes sur les cas nominaux
- aucune duplication de dispatch observee

### Lot 5 - Cutover dispatch/collect/merge planner

Objectif:

- faire du graphe la verite de dispatch et merge

Travail:

- deplacer la logique centrale de `planner_orchestrator_bridge.py` vers `planner_graph_runtime.py`
- laisser `parallel_workstream.py` comme adaptateur de mutation/projection seulement

Gate de sortie:

- une tache `READY_DEV -> DONE` passe integralement par le graphe
- crash apres dispatch puis reprise ne relance pas deux fois le meme subagent

### Lot 6 - Monitor/doctor event-store-first

Objectif:

- faire de `/api/status`, `/api/doctor`, `/api/agent-activity`, `/api/tasks/active` des lecteurs de verite durable

Travail:

- brancher monitor et doctor sur SQLite + projections stables
- garder les anciens calculs en fallback lecture seule temporaire

Gate de sortie:

- le monitor n'a plus besoin de relire les tails de logs pour la verite metier planner

### Lot 7 - Deprecation legacy

Objectif:

- retirer progressivement ce qui n'est plus canonique

Travail:

- geler `cron_tmux_role_runner.sh` comme wrapper d'appel temporaire
- retirer:
  - parser texte comme source de verite
  - planner-subagents registry comme canon
  - bus JSONL comme canon
  - heuristiques monitor construites seulement depuis logs

Gate de sortie:

- la plomberie legacy ne sert plus qu'a la compatibilite shell

## Scenarios de test obligatoires

1. `READY_DEV -> dispatch -> result -> proof -> DONE` via le graphe, projections board coherentes.
2. Crash apres `dispatch_capability` mais avant merge:
   reprise depuis checkpoint sans double dispatch.
3. Projection docs corrompue, store canonique sain:
   le planner continue sans `BOARD_READ_ERROR`.
4. Resultat subagent invalide:
   rejet type, zero mutation board, un evenement d'erreur unique.
5. `codex exec` indisponible temporairement:
   etat bloque/retryable sans corruption queue/workboard.
6. Erreur de syntaxe dans un helper Python annexe:
   `/api/status` et `fc_doctor` restent disponibles en mode degrade.
7. Double reception du meme resultat avec meme `invocation_id`:
   une seule mutation board.
8. Les projections `priority-queue.json` et `parallel-workstreams.json` restent compatibles pendant la migration.

## Raccourcis interdits

- brancher directement LangGraph a un provider API externe
- garder une projection docs dans le chemin critique de reprise planner
- laisser un dispatch sans `invocation_id` stable
- muter le board depuis plusieurs chemins concurrents hors `apply_workboard_mutation`
- utiliser `PydanticAI` comme prerequis coeur runtime si `Pydantic` suffit

## Impact sur les composants existants

### `planner_subagent_manager.py`

- reste un point de compatibilite temporaire
- perd progressivement la responsabilite de verite runtime
- devient client du `ModelInvocationPort` + producteur de `CapabilityResult`

### `planner_orchestrator_bridge.py`

- devient couche transitoire
- sa logique de decision/merge doit migrer vers `planner_graph_runtime.py`

### `parallel_workstream.py`

- conserve mutation/projection board
- n'est plus moteur de decision planner

### `apps/monitor/server.py`

- doit lire une vue agregee stable
- ne doit plus importer de modules metier fragiles pour calculer la sante canonique

## Plan de cutover

### Phase 1

- shadow mode ecriture event store + graph state
- legacy garde le dispatch et le merge

### Phase 2

- le graphe decide dispatch + collect + merge planner-only
- board et queue deviennent projections officielles

### Phase 3

- monitor et doctor lisent d'abord la nouvelle verite
- anciens chemins en fallback lecture seule courte

### Phase 4

- suppression progressive de la plomberie legacy non canonique

## Consequences

Positives:

- fin de la dependance aux projections JSON comme verite critique
- reprise durable et idempotente
- endpoints de sante plus robustes
- reduction de la dette bash/log parsing

Negatives:

- migration delicate car double runtime pendant une phase
- besoin de discipline stricte sur les side effects et idempotency keys
- cout initial de couture entre graphe, adapter et projections

## Decision operationnelle immediate

La prochaine execution ne doit pas commencer par `LangGraph` en production directe.

Le bon ordre pour ce depot est:

1. finir `Lot 0`
2. finir `Lot 1`
3. fiabiliser `Lot 2`
4. activer `Lot 4` shadow-write partout
5. seulement ensuite faire le cutover `Lot 5`

Le plan est donc accepte avec cette correction majeure:

- migration progressive vers un runtime canonique deja amorce
- pas de "big bang replacement"
