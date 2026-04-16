# BATCH-96-ARCH - Architecture continuity du 2026-04-16

Date: 2026-04-16T23:36:00Z
Owner: planner

## Architecture plan ref
- `docs/architecture/ARCHITECTURE_MAP.md`

## Architecture audit
- Canonical runtime refs: `AGENTS.md`, `docs/ops/ACTIVE_DOCS_INDEX.md`, `docs/ops/EC2_APP_RUNTIME_QUICK_REFERENCE.md`
- Product-serving runtime: EC2 public endpoints only; VM UTM reste control-plane/orchestration only.
- Impacted roots this tick: `apps/api`, `apps/web`, `platform/automation`
- Path target for downstream delivery:
  - `apps/api/src/domains/copilot/*`
  - `apps/api/src/domains/judge/*`
  - `apps/web/src/*`
  - `platform/automation/runtime/*`
- Anti-regression:
  - ne pas reintroduire `copilot-app/*`
  - ne pas reintroduire `backend/src/backend/src/*`
  - ne pas utiliser d'imports legacy `src.*`

## What changed today
- La verite produit visible a bascule vers l'EC2 public pour les smokes frontend/api/monitor.
- Les gardes runtime et plusieurs surfaces d'outillage ont ete realignees vers les endpoints publics EC2.
- `BATCH-96-ANALYSIS` a deja ferme le residu planner precedent; la tache active utile est maintenant la sortie ARCH vers delivery.

## What matters now
- Ne pas rouvrir un nouveau batch ni refaire une analyse.
- Ouvrir `BATCH-96-DEV-01` avec un scope delivery visible: brief du jour scope-first/portfolio-first sur les endpoints publics deja exposes.
- Garder le pattern Judge comme reference de repartition:
  - routes fines
  - logique dans `application/*`
  - contrats partages
  - preuve finale sur EC2 public

## Vision alignment
- batch=`BATCH-96`
- target=`unlock_dev01_for_scope_first_public_brief`
- impact=`ouvrir une tache dev canonique sur un delta utilisateur visible cote EC2 public`

## Next
- Completer `BATCH-96-ARCH`, puis laisser `BATCH-96-DEV-01` devenir la seule tache delivery canonique en aval.
