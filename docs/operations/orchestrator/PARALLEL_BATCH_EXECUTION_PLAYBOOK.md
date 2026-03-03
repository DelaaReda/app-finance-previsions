# Parallel Batch Execution Playbook (No Dependency Mode)

Updated: 2026-03-02

## Objective

Run batches in parallel without dependency chains while preserving quality, forecast integrity, and operational safety.

## Dispatch model

- Mode: `NO_DEPENDENCY_WAVES`
- Lanes:
- `L1_DATA_FOUNDATION`
- `L2_FORECAST_ENGINE`
- `L3_FORECAST_SCIENCE`
- `L4_GLOBAL_IMPACT`
- `L5_RELIABILITY_GOV`

## Wave policy

- `WAVE-A` (`P0`): strict QA gate, max concurrent roles 4.
- `WAVE-B` (`P1`): standard QA gate, max concurrent roles 3.
- `WAVE-C` (`P2`): standard QA gate, max concurrent roles 2.

## Mandatory role contract

Every role output must include:
- `STATUS`
- `DELTA`
- `EVIDENCE`
- `RISKS`
- `NEXT`
- `VERDICT`
- `BLOCKER_ID`
- `NEXT_ACTION_UNIQUE`

## No-dependency safety rules

- Each batch must be internally complete and demonstrable.
- Cross-batch assumptions are forbidden unless explicitly restated in `RISKS`.
- A batch can close even if another batch is open, only if its own evidence is complete.
- Any blocker must map to technical cause, not missing upstream batch.

## Anti-collision controls

- One active editing role per file area at a time.
- Use lane ownership to reduce collisions:
- `L1`: ingestion/contracts/freshness
- `L2`: forecast payload and engine behavior
- `L3`: calibration/drift/uncertainty science
- `L4`: geopolitical/legal/insider/supply-chain layers
- `L5`: reliability/ops/gates
- If collision detected, planner reassigns one role to next ready batch in same lane.

## Forecast-first guardrails

- Forecast outputs must include uncertainty and provenance.
- Free/public data required in nominal path for forecast layers.
- Degraded mode must be explicit when any required layer is stale/missing.
- No buy/sell execution behavior in this operating mode.

## Close criteria

A batch is closable only if:
- mandatory evidence keys are present,
- QA gate matches wave level requirements,
- blocker list is empty or downgraded with accepted rationale.

## Escalation triggers

- Repeated `signal_unparseable` for same role over 2 cycles.
- No new evidence produced over 2 cycles.
- Recurrent file collision in same lane.
- Forecast schema/provenance violation.
