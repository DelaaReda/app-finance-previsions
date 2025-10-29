# orchestrator.py

## Function: `run_pipeline`

Signature: `def run_pipeline(...)->dict`

Minimal sequential orchestrator (no external deps).

Steps (best‑effort):
- update-monitor (freshness)
- equity-forecast → forecast-aggregate
- macro-forecast
- llm-summary-run
- ui-health (optional; best effort)

Inputs:
- `step_budget`: int = 1
Returns: `dict`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
