# Finance App Roadmap (90 Days)

Updated: 2026-02-24
Scope: `/Users/venom/Documents/analyse-financiere/copilot-app`

## North-star outcomes
- Judge quality becomes measurable and stable (enough evaluated samples).
- Data pipeline reliability is high (freshness + failure visibility).
- Frontend/backed wiring is deterministic, documented, and testable.

## Baseline (current)
- Judge quality endpoint works but has low sample depth in many windows.
- Price/news ingestion exists with multiple sources and jobs.
- OpenClaw + WhatsApp + local memory are operational.

## Days 0-30: Data integrity first
### Goals
- Increase evaluated rows for `/api/judge/quality`.
- Remove avoidable data gaps in prices/news.

### Deliverables
- Standardize ticker mapping rules (`BRK.B`, aliases, exchange suffix handling).
- Enforce freshness SLAs per dataset (prices, news, macro, judge outputs).
- Add validation gates before judge run (required fields + minimum history depth).
- Raise per-ticker news context target to >=20 recent items over rolling 3 months.
- Persist ingestion diagnostics (source used, fallback reason, missing symbols).

### KPIs
- `coverage.with_price_series / total_rows >= 0.95`
- `coverage.evaluated_rows >= 50` (moving target, then 100+)
- Ingestion success rate >= 98% daily.

## Days 31-60: Forecast quality + calibration
### Goals
- Improve predictive signal and confidence calibration.

### Deliverables
- Add explicit calibration pipeline (bucket stats + recalibration policy).
- Add baseline comparators (naive trend, sector ETF baseline, random with same class balance).
- Separate short-horizon vs medium-horizon models/prompts (avoid one-size-fits-all).
- Add feature provenance in judge payload (what data influenced each call).
- Add regression suite for judge output schema + semantic constraints.

### KPIs
- Brier score trend improving over 4-week rolling window.
- `edge_vs_baseline > 0` sustained for target horizon(s).
- Calibration error reduced week over week.

## Days 61-90: Product hardening and delivery speed
### Goals
- Ship reliable operator workflows and cleaner UX wiring.

### Deliverables
- Frontend dashboard sections mapped to explicit backend contracts.
- Add end-to-end smoke suite (health, key endpoints, judge run, quality report).
- Add scheduled health reports (freshness, failed jobs, quality drift).
- Create incident runbooks for top 5 failure modes.
- Final cleanup pass: archive dead code paths, remove ambiguous script variants.

### KPIs
- Mean time to detect data breakage < 15 min.
- Mean time to restore < 60 min for common failures.
- Zero critical endpoint regressions across weekly releases.

## Weekly operating cadence (recommended)
- Monday: freshness + ingestion review.
- Wednesday: judge quality + calibration review.
- Friday: deploy window + post-deploy checklist.

## Immediate next actions (this week)
1. Add a `data_quality_gate` check before `judge_enrich` in the launcher flow.
2. Track daily `evaluated_rows` and `edge_vs_baseline` in one snapshot file.
3. Lock ticker normalization contract and test it with problematic symbols.
4. Add one frontend panel showing judge quality coverage health.
