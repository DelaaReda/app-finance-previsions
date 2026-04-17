# BATCH-96-ANALYSIS - Ce qui a change aujourd'hui et ce qui compte maintenant

Date: 2026-04-16T23:08:00Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/architecture/ARCHITECTURE_MAP.md`
- Active docs ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Runtime migration ref: `docs/ops/EC2_APP_RUNTIME_QUICK_REFERENCE.md`
- Pattern de reference: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Ce qui a change aujourd'hui
- Le runtime app-serving canonique a bascule vers l'EC2 public (`http://3.98.20.77/`, `http://3.98.20.77/api/...`, `http://3.98.20.77:8080/`); la VM UTM reste control-plane/orchestration only.
- Les surfaces runtime actives ont ete alignees sur ce modele: gardes produit, outils de verification, watchdogs et monitor visent maintenant les endpoints EC2 publics au lieu des loopbacks VM.
- La preuve produit du jour n'est donc plus "backend local repondu sur la VM", mais "endpoint public EC2 usable apres sync/restart".

## Ce qui compte maintenant
- Le prochain delta utile doit rester visible cote produit sur l'EC2 public: `copilot` et `personal-finance` doivent prioriser un brief scope-first/portfolio-first avec action ouverte en un clic.
- Le churn d'orchestration ne doit plus recreer de faux backlog local ou de faux blocage VM; les loopbacks VM et le monitor public restent advisory pour le produit tant qu'ils ne sont pas confirmes par le runtime canonique.
- A court terme, la priorite n'est pas un nouveau batch ni une refonte UI; c'est la convergence entre la verite planner et la verite publique EC2 avec un delta utilisateur clair.

## Architecture audit compact
- Paths impactes: `apps/api`, `apps/web`, `apps/monitor`, `platform/automation`, `scripts/aws_remote_app_control.sh`
- Anti-regression: ne pas toucher `copilot-app/*`, `backend/src/backend/src/*`, ni imports legacy `src.*`
- Reuse-first: conserver `apps/api/src/domains/judge/application/*` comme reference de repartition, garder `apps/api/src/domains/copilot/*` comme adaptateur produit, et prouver le comportement via les endpoints publics EC2.

## Vision alignment
- Batch cible: rendre la porte d'entree produit fiable et scope-first sur les endpoints publics deja exposes.
- Impact attendu: l'utilisateur voit un brief du jour utile, une action priorisee pertinente, et un memo d'investissement ouvrable sans dependre d'une lecture control-plane locale.

## Next
- Reprendre `BATCH-96-ANALYSIS` pour le fermer proprement avec un dispatch concret vers la prochaine tache canonique utile, sans recreer de batch parallele.
