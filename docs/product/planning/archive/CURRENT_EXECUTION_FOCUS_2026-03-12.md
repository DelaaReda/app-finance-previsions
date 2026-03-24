---
status: canonical
last_verified: 2026-03-12
---

Superseded on 2026-03-13 by [CURRENT_EXECUTION_FOCUS_2026-03-13.md](/home/venom/analyse-financiere/docs/product/planning/CURRENT_EXECUTION_FOCUS_2026-03-13.md).

# Current Execution Focus - 2026-03-12

## Purpose
Realign the current planning cycle to the live runtime board/queue truth and remove active agent ambiguity between `VB-*` and `BATCH-*`.

Canonical references:
- [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- [BACKEND_FIRST_PRODUCT_BACKLOG.md](/home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md)
- [PLANNER_GLOBAL_MISSION.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_GLOBAL_MISSION.md)
- [PLANNER_DELIVERY_OPERATING_RULES.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_DELIVERY_OPERATING_RULES.md)
- [VISION_ALIGNED_DELIVERY_BATCHES_2026-03-12.md](/home/venom/analyse-financiere/docs/product/planning/VISION_ALIGNED_DELIVERY_BATCHES_2026-03-12.md)

## Active cycle truth
- Dispatch namespace for the current cycle: `BATCH`
- Canonical runtime source: `docs/operations/orchestrator/priority-queue.json` and `docs/operations/orchestrator/parallel-workstreams.json`
- Active delivery batch: `BATCH-23`
- Recently completed reference batch: `BATCH-22`
- Historical bridge namespace: `VB-*` is reference-only and must not be dispatched

## Repo truth observed on 2026-03-12
- `BATCH-22` is closed as the immediate previous product/value batch in the active runtime window.
- `BATCH-23` is the current dispatchable batch and is exposed as `READY_DEV`.
- The immediate runtime next action is to claim `BATCH-23-DEV-02`.
- `BATCH-24` and `BATCH-25` remain queued behind `BATCH-23` in the current runtime chain.
- The `VB-*` documents still matter as product-history context, but they no longer define what workers should dispatch next.

## Immediate planner move
Start from `BATCH-23`.

Required planner behavior:
- dispatch only from the active `BATCH-*` namespace for the current cycle
- keep `BATCH-22` available as the recent completion/proof reference
- treat any `VB-*` mention in active agent-facing paths as historical unless a document dated after 2026-03-12 explicitly reactivates it
- surface drift whenever queue/workboard `active_cycle` and planning docs disagree

## Alignment rule
The current cycle is considered aligned only when all of the following are true:
- queue and workboard expose the same `active_cycle`
- `active_cycle.doc_ref` points to this document
- `active_cycle.dispatch_namespace` is `BATCH`
- `active_cycle.active_batch_ids` contains `BATCH-23`
- agent-facing planning indexes route to the `2026-03-12` cycle docs first

## Non-goals for this pass
- no product-contract redefinition for `brief`, `copilot/start`, `copilot/context`, or `copilot/ask`
- no automatic documentation generation from runtime state yet
- no reactivation of `VB-*` as a second live namespace
