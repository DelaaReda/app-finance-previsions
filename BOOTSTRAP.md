# BOOTSTRAP.md - Agent Onboarding (Finance Copilot)

Ce fichier est le point d’entrée opérationnel pour tout nouvel agent.
Objectif: être autonome vite, livrer sans dérive, et respecter la vision produit.

## 1) Lecture obligatoire (ordre)
1. `AGENTS.md`
2. `SOUL.md`
3. `USER.md`
4. `memory/YYYY-MM-DD.md` (aujourd’hui + hier)
5. `MEMORY.md` (main session seulement)
6. `docs/planning/PRODUCT_VISION.md`
7. `docs/planning/tasks.md` (source unique des tâches)

## 2) Règles de travail (non négociables)
- Safety shell:
  - toujours passer par `scripts/exec_safe.sh`
- Co-édition multi-agents:
  1. claim d’abord: `python3 scripts/parallel_workstream.py claim --role <role>`
  2. publier un `INTENT` dans `docs/ops/ADMIN_TEAM_CHAT.md` avant édition cross-section
  3. patch minimal sur le scope ciblé
  4. en cas de collision: merge explicite, ne jamais écraser silencieusement
- Source unique des tâches:
  - `docs/planning/tasks.md`
  - pas de création de tâches dans les docs Scrum/backlog
- Contrat de sortie agent (obligatoire):
  - `STATUS / DELTA / EVIDENCE / RISKS / NEXT / VERDICT / BLOCKER_ID / NEXT_ACTION_UNIQUE`

## 3) Vision produit (résumé)
Produit: copilot finance personnel pour un investisseur solo, non expert finance, qui manque de temps.

But utilisateur:
- obtenir en 2-3 clics “quoi faire aujourd’hui” sur son portefeuille
- réduire fortement le temps de veille/recherche
- conserver un coût runtime faible

Différenciateur non négociable:
- fournir des **prévisions data-driven** (API + UI), pas seulement des résumés textuels.

Contraintes:
- personal-first (single user)
- low-cost runtime (providers gratuits/faible coût priorisés)
- fraîcheur cible quasi temps réel (écart ~10 minutes acceptable)

Référence: `docs/planning/PRODUCT_VISION.md`

## 4) MVP (définition)
MVP cœur:
1. Forecast par actif/secteur (`direction`, `confidence`, `action`, `horizon`, `why`, `risk_flag`, `updated_at`)
2. Multi-model consensus + Judge
3. Ask Copilot (réponse orientée action + contexte + risques)

Flux MVP attendu:
- ouverture app
- brief quotidien actionnable en <= 3 clics
- états `fresh/stale/degraded` visibles

## 5) Basic-ready (cible opérationnelle)
La baseline “app prête basique” est atteinte si:
- les epics obligatoires passent: 1, 2, 3, 4, 5, 8, 10, 11, 13, 14, 15, 16
- flux utilisateur passe:
  - ouvrir app -> brief <= 3 clics
  - forecasts retournés par pipeline data/model (pas uniquement heuristique) + provenance visible (nominal/degraded)
  - preuve API->UI: decision cards/brief/judge/ask affichent les champs forecast + provenance (aucun fallback caché)
  - Judge et Ask fonctionnels avec réponses exploitables
  - freshness/degraded/runtime visibles
  - gate final sans blocker critique

Référence: section `Continuous Delivery Loop` dans `docs/planning/tasks.md`

## 6) Carte des epics (actifs)
- P0: 1, 2, 3, 15, 16
- P1: 4, 5, 8, 10, 11, 12, 13, 14
- P2: 6, 7, 9

Voir:
- `docs/planning/epics.md`
- `docs/scrum/product-backlog.md` (vue priorités uniquement)

## 7) Arbo technique essentielle
- Backend API: `copilot-app/backend/src/api/main.py`
- Routes: `copilot-app/backend/src/api/routes/`
- Frontend runtime: `copilot-app/frontend/app/app.js`
- UI shell: `copilot-app/frontend/app/index.html`, `style.css`
- Board tâches: `docs/planning/tasks.md`
- Gates/scripts: `scripts/`
- Artefacts: `finance-app/openclaw-gates/`

## 8) Workflow autonome (coding)
1. Claim la tâche.
2. Lire strictement la section de la tâche dans `tasks.md` (scope/deps/tests).
3. Implémenter le plus petit delta utile.
4. Valider localement (tests ciblés puis gate).
5. Produire les preuves (commandes + résultats).
6. Mettre à jour handoff/état si nécessaire.
7. En cas de blocage: remonter immédiatement `BLOCKER_ID` + action unique.

## 9) Commandes de base (golden path)
Depuis la racine du repo sur la VM (ex: `/home/venom/analyse-financiere` ou `/home/venom/shared/analyse-financiere` selon mount):

```bash
PROJECT_ROOT="/home/venom/analyse-financiere"
scripts/exec_safe.sh --workdir "$PROJECT_ROOT" -- "python3 scripts/parallel_workstream.py claim --role <role>"
scripts/exec_safe.sh --workdir "$PROJECT_ROOT" -- "bash scripts/preflight_dispatch.sh"
scripts/exec_safe.sh --workdir "$PROJECT_ROOT" -- "bash scripts/backend_regression_gate.sh --no-live"
scripts/exec_safe.sh --workdir "$PROJECT_ROOT" -- "bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/<artifact>.md"
```

## 10) Definition of Done (pratique)
Une tâche est DONE seulement si:
- scope IN respecté (sans dérive)
- tests/validations exécutés
- preuves publiées
- verdict explicite (`PASS` ou `BLOCKED`)
- prochaine action unique claire

## 11) Erreurs fréquentes à éviter
- créer des tâches dans `sprint-next.md` ou `product-backlog.md`
- modifier plusieurs zones non liées “par opportunité”
- masquer un échec test derrière un texte optimiste
- changer des contrats API sans tests de contrat
- fallback caché côté UI (toujours rendre le dégradé visible)

## 12) Checklist 30 minutes (nouvel agent)
1. Lire les fichiers obligatoires (section 1).
2. Claim une tâche.
3. Poster INTENT dans `ADMIN_TEAM_CHAT.md`.
4. Vérifier dépendances/scope de la tâche.
5. Lancer implémentation + validations.
6. Publier verdict contractuel complet.

## 13) Mémoire et continuité
- Journal court terme: `memory/YYYY-MM-DD.md`
- Contexte long terme: `MEMORY.md`
- Si tu apprends une règle utile -> documente-la immédiatement.

---

Si un point est ambigu, privilégier:
1) la sécurité, 2) le board `tasks.md`, 3) la preuve exécutable.
