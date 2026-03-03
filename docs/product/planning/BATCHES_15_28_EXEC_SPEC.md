# BATCHES 15-28 - Expansion Execution Spec

Updated: 2026-03-02
Scope: expansion creative aligned with personal-first finance copilot vision.

## Phase D - Decision Intelligence Expansion (BATCH-15 to BATCH-19)

## BATCH-15 - Strategy Playbooks Engine
Epics:
- E15.1 Strategy playbooks by regime and risk profile.
- E15.2 Playbook aware recommendation generation.
- E15.3 Conflict and override visibility.
Tasks:
- `B15-T1` backend: playbook schema + resolver.
- `B15-T2` frontend: playbook selector in copilot UI.
- `B15-T3` data: map signals to playbook confidence.
- `B15-T4` qa: conflict scenario tests.
Acceptance:
- Recommendation always includes `playbook_id`.
- Conflict warning visible when signal and playbook diverge.

## BATCH-16 - Scenario and Stress Testing Lite
Epics:
- E16.1 Scenario engine.
- E16.2 Stress catalog and default templates.
- E16.3 Actionable output for risk management.
Tasks:
- `B16-T1` backend: scenario endpoint for macro and asset shocks.
- `B16-T2` data: baseline scenario assumptions.
- `B16-T3` frontend: compare scenario results panel.
- `B16-T4` planner: map scenario outputs to actions.
Acceptance:
- At least 5 predefined scenarios available.
- Scenario output includes impact, confidence, and action.

## BATCH-17 - Regime Detection and Allocation Drift Alerts
Epics:
- E17.1 Regime classification.
- E17.2 Allocation drift detection.
- E17.3 Posture guidance matrix.
Tasks:
- `B17-T1` backend: regime classifier endpoint.
- `B17-T2` data: threshold calibration and drift backtest.
- `B17-T3` frontend: regime banner and drift alerts.
- `B17-T4` planner: posture recommendation table.
Acceptance:
- Dashboard and copilot include regime label and confidence.
- Drift alerts trigger with clear threshold reason.

## BATCH-18 - Event Driven Copilot
Epics:
- E18.1 Event calendar ingestion.
- E18.2 Event impact scoring.
- E18.3 Event aware recommendations.
Tasks:
- `B18-T1` backend: critical events endpoint (macro + earnings).
- `B18-T2` data: event impact prior per asset class.
- `B18-T3` frontend: 24h/48h event timeline.
- `B18-T4` planner: timing aware recommendation rules.
Acceptance:
- Daily brief includes critical upcoming events.
- Copilot output includes event timing risk note when relevant.

## BATCH-19 - Explainability Graph and Source Traceability
Epics:
- E19.1 Decision evidence graph.
- E19.2 Source quality and freshness scoring.
- E19.3 Explainability UX.
Tasks:
- `B19-T1` backend: weighted evidence graph payload.
- `B19-T2` frontend: source trace panel.
- `B19-T3` qa: source link validity checks.
- `B19-T4` planner: explainability contract gate.
Acceptance:
- Recommendation shows weighted sources and freshness markers.
- Broken source link count in gate evidence equals zero.

## Phase E - Personal Risk and Execution Discipline (BATCH-20 to BATCH-23)

## BATCH-20 - Personal Policy Guardrails
Epics:
- E20.1 User policy model.
- E20.2 Enforcement in recommendation pipeline.
- E20.3 Override governance.
Tasks:
- `B20-T1` backend: policy validator service.
- `B20-T2` frontend: policy editor and violation badge.
- `B20-T3` qa: hard stop and downgrade tests.
- `B20-T4` planner: override decision workflow.
Acceptance:
- Policy violating recommendation never appears as plain BUY.
- Policy revisions are versioned with timestamp.

## BATCH-21 - Paper Trading Simulator and Execution Journal
Epics:
- E21.1 Virtual execution engine.
- E21.2 Execution journal lifecycle.
- E21.3 Recommendation to execution feedback.
Tasks:
- `B21-T1` backend: paper execution endpoint with fee/slippage params.
- `B21-T2` frontend: execute and track paper trade flow.
- `B21-T3` data: execution quality metrics.
- `B21-T4` planner: bridge decision card to trade action.
Acceptance:
- Paper trade can start from recommendation screen.
- Journal stores fill assumptions and resulting PnL.

## BATCH-22 - Rebalancing Optimizer Lite
Epics:
- E22.1 Constraint based rebalance optimizer.
- E22.2 One screen rebalance proposal.
- E22.3 Policy aware feasibility checks.
Tasks:
- `B22-T1` backend: optimization endpoint.
- `B22-T2` data: turnover and concentration metrics.
- `B22-T3` frontend: rebalance proposal card.
- `B22-T4` qa: infeasible scenario handling.
Acceptance:
- Feasible solution rate >= 95 percent on fixture set.
- Rebalance proposal always includes risk and turnover delta.

## BATCH-23 - Tax, Fees, and Slippage Awareness
Epics:
- E23.1 Cost model in decision payload.
- E23.2 Net impact presentation.
- E23.3 Low edge warning.
Tasks:
- `B23-T1` backend: cost estimator bands by asset.
- `B23-T2` frontend: gross versus net impact view.
- `B23-T3` data: default fee and slippage calibration.
- `B23-T4` planner: net edge wording rules.
Acceptance:
- Actionable outputs include gross and net expected effect.
- High cost warning triggers when net advantage is small.

## Phase F - Routine Automation and Operational Maturity (BATCH-24 to BATCH-28)

## BATCH-24 - Alerting Intelligence V2
Epics:
- E24.1 Priority alert queue.
- E24.2 Dedup and fatigue control.
- E24.3 Alert center UX.
Tasks:
- `B24-T1` backend: dedup plus suppression windows.
- `B24-T2` data: precision recall tuning.
- `B24-T3` frontend: alert center with urgency tiers.
- `B24-T4` planner: fatigue governance policy.
Acceptance:
- Duplicate alerts materially reduced.
- Critical alerts surface under one minute.

## BATCH-25 - Autonomous Morning Brief Pipeline
Epics:
- E25.1 Scheduled brief generation.
- E25.2 Action oriented summary template.
- E25.3 Failure handling and degraded fallback.
Tasks:
- `B25-T1` backend: digest job and cache artifact.
- `B25-T2` infra: job monitor and retry strategy.
- `B25-T3` frontend: morning brief single screen.
- `B25-T4` planner: top three actions rubric.
Acceptance:
- Morning brief generated before configured hour.
- On failure, degraded brief is explicit and usable.

## BATCH-26 - Weekly Investment Committee Mode
Epics:
- E26.1 Weekly summary pack.
- E26.2 Committee mode UI.
- E26.3 Carry over action tracking.
Tasks:
- `B26-T1` backend: weekly pack endpoint.
- `B26-T2` data: weekly KPI and transition metrics.
- `B26-T3` frontend: committee deck style view.
- `B26-T4` planner: weekly rubric and follow ups.
Acceptance:
- One click weekly packet with outcomes and next steps.
- Carry over actions persist across weeks.

## BATCH-27 - Reliability SRE Pack and Chaos Drills
Epics:
- E27.1 Runtime SLO observability.
- E27.2 Chaos drills and recovery evidence.
- E27.3 Reliability blocker burn down.
Tasks:
- `B27-T1` infra: uptime/latency/queue health dashboards.
- `B27-T2` qa: chaos drills suite.
- `B27-T3` backend: resilience fixes from findings.
- `B27-T4` planner: reliability gate decision.
Acceptance:
- Drill evidence includes recovery commands and timing.
- Open P0 reliability blockers equals zero at gate.

## BATCH-28 - MVP v3 Release Gate and Adoption Analytics
Epics:
- E28.1 Consolidated final release gate.
- E28.2 Adoption and utility analytics.
- E28.3 Final E2E validation nominal and degraded.
Tasks:
- `B28-T1` planner: final GO/NO-GO dossier.
- `B28-T2` data: adoption metrics pack (daily usage utility).
- `B28-T3` frontend: telemetry panel for time to decision and click depth.
- `B28-T4` qa: final E2E proof set.
Acceptance:
- Final gate includes all mandatory artifacts and blocker inventory.
- Adoption metrics prove sustained daily utility.

## Priority recommendation for dispatch

1. `BATCH-15`, `BATCH-16`, `BATCH-17` first (decision quality).
2. `BATCH-20` before `BATCH-21/22` (risk guardrails before action automation).
3. `BATCH-27` and `BATCH-28` as mandatory final gate before broad reactivation.
