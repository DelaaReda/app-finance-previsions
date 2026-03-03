# BATCHES 41-50 - Global Multi-Layer Forecast Spec

Updated: 2026-03-02
Scope: prediction and analysis only (no buy/sell execution).
Constraint: free/public data in nominal runtime path.

## Global objective

Deliver a forecast board able to explain expected impacts at all layers:
- company
- sector
- country
- continent
- world

and across key drivers:
- geopolitics and conflicts
- legal/policy change
- insider behavior
- supply chain and commodity shocks

## BATCH-41 - Free Global Signal Mesh
Epics:
- E41.1 Free source inventory and licensing.
- E41.2 Unified ingestion contracts.
- E41.3 Health and freshness observability.
Acceptance:
- No paid dependency in nominal forecast path.
- Source provenance and license class attached to each feed.

## BATCH-42 - Geopolitical Risk Graph and Conflict Escalation
Epics:
- E42.1 Event-to-risk graph modeling.
- E42.2 Escalation scoring.
- E42.3 World/continent/sector exposure views.
Acceptance:
- Forecast payload includes geopolitical layer contribution.
- Escalation alerts visible with timestamp and region.

## BATCH-43 - Law and Policy Change Impact Engine
Epics:
- E43.1 Policy event extraction.
- E43.2 Jurisdiction-to-sector/company impact mapping.
- E43.3 Effective-date timeline analytics.
Acceptance:
- Policy change fields present in forecast narratives when relevant.
- Status proposed/adopted/effective visible in UI.

## BATCH-44 - Insider Behavior Intelligence Layer
Epics:
- E44.1 Public insider data parsing.
- E44.2 Feature engineering with uncertainty.
- E44.3 Conservative interpretation guardrails.
Acceptance:
- Insider signal has provenance and uncertainty.
- No deterministic language from insider-only evidence.

## BATCH-45 - Supply Chain and Commodity Shock Propagation
Epics:
- E45.1 Shock propagation modeling.
- E45.2 World-to-company exposure chains.
- E45.3 Assumption governance.
Acceptance:
- Exposure chain shown from macro shock to company forecast.
- Assumptions versioned and auditable.

## BATCH-46 - Country/Continent/World Macro Regime Forecasts
Epics:
- E46.1 Hierarchical regime modeling.
- E46.2 Cross-level consistency checks.
- E46.3 Multi-scale visualization.
Acceptance:
- Country, continent, world forecasts available with confidence.
- Contradictions flagged with consistency diagnostics.

## BATCH-47 - Sector-to-Company Impact Transmission
Epics:
- E47.1 Transmission coefficients.
- E47.2 Company impact decomposition.
- E47.3 Uncertainty-aware confidence degradation.
Acceptance:
- Company view includes sector transmission factors.
- Confidence adapts when transmission uncertainty rises.

## BATCH-48 - Event Impact Horizon Matrix
Epics:
- E48.1 Event class prior modeling by horizon.
- E48.2 Matrix API and UX.
- E48.3 Horizon interpretation templates.
Acceptance:
- Event-driven forecast shows 1d/1w/1m impact matrix.
- Templates explain cross-horizon divergence.

## BATCH-49 - Multi-Layer Forecast Fusion and Attribution
Epics:
- E49.1 Multi-layer fusion engine.
- E49.2 Attribution stability controls.
- E49.3 Contribution transparency UX.
Acceptance:
- Output includes normalized contribution weights per layer.
- Attribution stability checks pass under perturbation tests.

## BATCH-50 - Global Forecast Board Final Gate (Free Data)
Epics:
- E50.1 Multi-layer E2E validation.
- E50.2 Free-data compliance and runtime SLA.
- E50.3 Quality trend consolidation.
Acceptance:
- Final gate proves all required layers active and traceable.
- Free/public data compliance validated for nominal runtime.
- Quality trend non-regressing across horizons and layers.

## Mandatory evidence schema additions

- `FREE_DATA_SOURCE_CATALOG_PROOF`
- `LICENSE_COMPLIANCE_PROOF`
- `GEOPOLITICAL_GRAPH_PROOF`
- `POLICY_CHANGE_DETECTION_PROOF`
- `INSIDER_SIGNAL_PROOF`
- `SHOCK_PROPAGATION_PROOF`
- `HIERARCHICAL_REGIME_PROOF`
- `TRANSMISSION_MODEL_PROOF`
- `EVENT_HORIZON_MATRIX_PROOF`
- `FUSION_ENGINE_PROOF`
- `FINAL_GLOBAL_FORECAST_GATE_PROOF`

## Non-negotiable guardrails

- Forecast payloads must include uncertainty and provenance.
- Missing or stale layers must degrade explicitly, never silently.
- Recommendations remain analytical guidance; no order execution behavior.
