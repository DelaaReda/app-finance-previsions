# BATCH-53 — Orchestration reliability: READY->CLAIM materialization [ANALYSIS]

Date: 2026-03-06T03:44:00Z
Role: planner
Upstream: docs/operations/orchestrator/proofs/BATCH-53-PLAN-20260306T0322Z.md

## Vision alignment
Source: docs/product/planning/PRODUCT_VISION.md
Goal: accelerer la livraison en reduisant les stalls READY->CLAIM (planner/dev).

## Architecture plan ref
Reference: docs/architecture/ARCHITECTURE_MAP.md

## Reproduction (observed)
- queue_has_ready=1 mais claim planner retourne NO_READY_TASK a plusieurs ticks.
- Impact: BATCH-11-ARCH (annoncé READY) n'est pas materialisé en tache READY planner.

## Dependency policy (enforced)
batch_dependency_policy: single_batch
batch_merge_strategy: intra_batch_sequencing

## Architecture audit (paths impactés)
- apps/web/src
- apps/api/src/domains
- apps/api/runtime
- platform/automation

## Acceptance gate (ANALYSIS -> ARCH)
1) Apres sync-priority, une tache planner READY doit etre claimable (sinon issue ouverte + proof).
2) Artefact ARCH doit contenir audit chemins + policy single_batch.

