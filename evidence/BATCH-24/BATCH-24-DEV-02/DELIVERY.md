# BATCH-24-DEV-02

## Slice

- Reused the existing alerts timeline surface in `apps/web/src/domains/forecasts/pages/app.js`.
- Wired additive `/api/alerts` queue metadata through `apps/web/src/domains/forecasts/contracts/apiConnector.js`.
- Kept the change on the current alerting path; no new frontend subsystem was introduced.

## Before / After

- Before: the connector flattened `/api/alerts` to a raw alert array, so additive queue metadata from `DEV-01` was dropped before it reached the existing alert center.
- After: the connector preserves `suppressed_count`, `queue.top_priority_band`, `stats.priority_bands`, `stats.suppression_reasons`, `pipeline.suppression_window_minutes`, and per-alert priority/suppression fields while still hydrating `window.alertTimeline`.

## Existing UI Wiring Reused

- `/api/alerts`
- `getAlerts()`
- `transformAlert()`
- `window.alertTimeline` and `window.alertTimelineMeta`
- existing alert ordering/filtering/rendering in `apps/web/src/domains/forecasts/pages/app.js`

## Proof

- Targeted contract proof: `apps/web/src/domains/forecasts/contracts/apiConnector.test.js`
- Existing visible-surface proof: `apps/web/src/domains/forecasts/pages/app.test.js`
- Verified strings on the existing alert surface:
  - `Top queue: MSFT Risk • Urgent queue`
  - `Urgent 1`
  - `Action 1`

## Residual Edge For DEV-03

- none
