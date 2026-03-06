# BATCH-52 — Document de reference agents (operational) [ANALYSIS]

Date: 2026-03-06T02:44:00Z
Role: planner
Upstream: docs/operations/orchestrator/proofs/BATCH-52-PLAN-20260306T0222Z.md

## Vision alignment
Source: docs/product/planning/PRODUCT_VISION.md
Impact: stabiliser l'orchestration (READY->CLAIM) accelere la livraison Finance Copilot (MVP v3) en reduisant les stalls multi-roles.

## Architecture plan ref
Reference: docs/architecture/ARCHITECTURE_MAP.md

## Constats
- Plusieurs signaux queue READY sans tache planner READY materialisee -> necessite sync-priority fiable et preuves auditees.
- Les proofs manquants (architecture_audit) degradent le guardian et la traçabilite.

## Dependency policy (enforced)
batch_dependency_policy: single_batch
batch_merge_strategy: intra_batch_sequencing

## Architecture audit (paths impactés)
- apps/web/src
- apps/api/src/domains
- apps/api/runtime
- platform/automation

## Acceptance gate (ANALYSIS -> ARCH)
1) Chaque artefact planner doit inclure: vision_alignment, architecture_plan_ref, architecture_audit.
2) Aucun depends_on_batch top-level: sequencing intra-batch uniquement.
3) Pour chaque DEV-01: fichiers cibles + test cible (smoke/e2e minimal) explicités.

