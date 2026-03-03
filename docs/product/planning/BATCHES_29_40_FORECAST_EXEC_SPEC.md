# BATCHES 29-40 - Forecast-First Expansion Spec

Updated: 2026-03-02
Scope: analysis and prediction only, no execution-trading intent.

## Core principle

- All outputs prioritize forecast quality, uncertainty communication, and explainability.
- No batch in this pack is designed to trigger buy/sell execution workflows.

## BATCH-29 - Probabilistic Forecast Calibration Lab
Epics:
- E29.1 Calibration metrics and targets.
- E29.2 Reliability diagnostics API.
- E29.3 Reproducible calibration gates.
Tasks:
- data: reliability curve, calibration error by horizon.
- backend: diagnostics endpoint.
- qa: rerun reproducibility checks.
- planner: threshold policy and gate.

## BATCH-30 - Multi-Horizon Forecast Decomposition
Epics:
- E30.1 Driver decomposition by horizon.
- E30.2 Divergence interpretation.
- E30.3 Decomposition visualization.
Tasks:
- backend: decomposition payload.
- data: contribution validation.
- frontend: horizon decomposition cards.
- planner: interpretation rules in brief.

## BATCH-31 - Cross-Asset Correlation Regime Map
Epics:
- E31.1 Rolling correlation engine.
- E31.2 Regime shift detection.
- E31.3 Correlation-aware narratives.
Tasks:
- data: correlation and shift metrics.
- backend: regime map endpoint.
- frontend: heatmap widget.
- planner: narrative linkage policy.

## BATCH-32 - Forecast Ensemble Governance
Epics:
- E32.1 Dynamic provider weighting.
- E32.2 Provider reliability scoring.
- E32.3 Degraded fallback governance.
Tasks:
- backend: weighting engine.
- data: reliability scoring.
- qa: outage fallback tests.
- planner: governance rules.

## BATCH-33 - Macro Narrative-to-Signal Parser
Epics:
- E33.1 Macro factor taxonomy.
- E33.2 Narrative parsing quality.
- E33.3 Factor visibility in analysis views.
Tasks:
- backend: parser service.
- data: extraction benchmark.
- frontend: factor chips and tooltips.
- planner: taxonomy governance.

## BATCH-34 - Alternative Data Sentiment Fusion
Epics:
- E34.1 Sentiment normalization.
- E34.2 Feature fusion.
- E34.3 Source quality weighting.
Tasks:
- data: normalization pipeline.
- backend: fused feature payload.
- frontend: sentiment strip.
- planner: weighting policy.

## BATCH-35 - Forecast Drift Sentinel and Auto-Recalibration
Epics:
- E35.1 Drift monitoring.
- E35.2 Safe recalibration workflow.
- E35.3 Audit and rollback readiness.
Tasks:
- data: drift detector.
- backend: recalibration orchestration.
- infra: drift alerting.
- planner: guardrails and rollback criteria.

## BATCH-36 - Uncertainty Visualization UX
Epics:
- E36.1 Percentile outputs.
- E36.2 Confidence band UI.
- E36.3 Language anti-overconfidence.
Tasks:
- backend: percentile payload.
- frontend: uncertainty components.
- data: interval coverage validation.
- planner: wording guide.

## BATCH-37 - Hypothesis Workbench
Epics:
- E37.1 Structured hypothesis authoring.
- E37.2 Forecast-backed analysis response.
- E37.3 Searchable hypothesis history.
Tasks:
- frontend: hypothesis builder.
- backend: query orchestration.
- data: validation templates.
- planner: review workflow.

## BATCH-38 - Walk-Forward Forecast Scoreboard
Epics:
- E38.1 Walk-forward pipeline.
- E38.2 Rolling quality dashboard.
- E38.3 Quality-bar enforcement.
Tasks:
- data: walk-forward metrics.
- backend: scorecard endpoint.
- frontend: quality dashboard.
- planner: threshold policy.

## BATCH-39 - Forecast Data Quality SLA and Provenance
Epics:
- E39.1 Provenance schema.
- E39.2 SLA monitoring.
- E39.3 Integrity validation.
Tasks:
- backend: provenance block in forecast payload.
- infra: SLA probes and alerts.
- qa: provenance integrity tests.
- planner: incident handling policy.

## BATCH-40 - Predictive Research Hub Finalization Gate
Epics:
- E40.1 Forecast-only release gate.
- E40.2 E2E analysis validation.
- E40.3 Quality trend non-regression report.
Tasks:
- planner: final dossier and blocker inventory.
- qa: final E2E suite.
- data: long trend report.
- frontend: research hub polish for daily analysis.

## Cross-batch acceptance targets

- Forecast schema validity: 100 percent.
- Confidence and uncertainty fields present: at least 95 percent.
- Freshness SLA compliance on core data: at least 90 percent.
- Explainability/provenance coverage: 100 percent on core endpoints.
- No deterministic language when uncertainty is high.
