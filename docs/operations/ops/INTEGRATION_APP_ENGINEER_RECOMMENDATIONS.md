# Integration App Engineer Recommendations (Reuse-First Checklist)

Objective: improve delivery quality and coordination by forcing "reuse-first" behavior
across backend, frontend, and integration work. This is a lightweight checklist that
should be copied into tasks and used as a review lens.

## Tagging (stable marker)

Use this prefix in task notes (workboard), planning docs, and PR descriptions:
- `INTEGRATION-APP-EENGINEER-RECOMMENDATIONS: ...`

Legacy alias (same meaning, accepted for search/backward compat):
- `INTEGRATION-APP-ENGINEER-RECOMMENDATIONS: ...`

## Rules (do these before writing new code)

- Search for reuse candidates first:
  - `rg -n \"<keyword>\" copilot-app/backend/src copilot-app/backend/services copilot-app/backend/storage copilot-app/backend/models copilot-app/backend/jobs copilot-app/frontend/app`
- Prefer wiring existing modules/services over creating new helpers.
- Prefer extending canonical paths (`copilot-app/backend/src/...`) instead of adding a third location.
- If you must add a new module, update the reuse catalog:
  - `docs/ops/REUSE_MODULES_CATALOG.md`

## Backend: endpoint implementation standards

- Copy the Judge endpoint pattern for new endpoints:
  - stable response envelope (`ok/data`) + never-empty fallback
  - TTL cache + deterministic cache keys
  - `debug=true` query mode: bypass cache and expose debug payload only in debug
  - strict parsing/validation when using LLMs (Pydantic + JSON strict)
  - multi-provider fallback chain without breaking the contract
- Canonical reference docs:
  - `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`
  - `docs/ops/REUSE_MODULES_CATALOG.md`

Judge reference stack (do not re-invent):
- `copilot-app/backend/src/api/routes/judge.py`
- `copilot-app/backend/src/services/judge_pipeline.py`
- `copilot-app/backend/src/services/g4f_client.py`
- `copilot-app/backend/src/services/judge_builder.py`
- `copilot-app/backend/src/schemas/judge.py`

## Frontend: reuse widgets/components first

- Reuse existing widgets before creating new components:
  - `copilot-app/frontend/app/components/widgets/*`
- Reuse existing wiring patterns:
  - `copilot-app/frontend/app/app.js`
- Any new UI component must justify why an existing widget cannot be adapted.

## Integration / QA: proof and gates

- Prefer existing test harness and gates:
  - `bash scripts/backend_regression_gate.sh --no-live`
  - `bash scripts/backend_regression_gate.sh` (when backend is up)
- Do not invent a new test runner for one endpoint unless there is a hard blocker.
- Ensure artifacts are linked in the workboard task (proof manifests, gate reports).

## Definition of Done (minimum)

- Reuse evidenced: notes mention the exact modules/components reused.
- Contract parity: stable response shape + never-empty fallback + debug mode (when applicable).
- Tests/gates: at least the backend regression gate is green, with a short human `run_note`.

