# Finance App Decisions And Open Items

Updated: 2026-02-24

## Decisions locked
- Active app path is `copilot-app` (not `finance-app` directory).
- Judge quality relies on refreshed prices + timestamped forecast rows.
- OpenClaw long-term memory is enabled with local embeddings model.
- WhatsApp channel is linked and operational for OpenClaw.

## Current known issue
- OpenClaw CLI version `2026.2.22-2` still reports `channels.whatsapp.enabled` as an unknown key in doctor output.
- This appears to be a tooling-level false warning; channel behavior is functional.

## Data-quality priorities
- Ensure enough evaluated samples for `/api/judge/quality` (current bottleneck is low evaluated rows).
- Keep per-ticker news depth high for LLM context (target >= 20 recent items over rolling 3 months where possible).
- Maintain clean ticker mapping and symbol normalization (example edge case: `BRK.B`).

## Next engineering priorities
- Expand forecast/evaluation coverage to increase statistical significance.
- Harden ingest retries and freshness alerts around price/news jobs.
- Maintain endpoint contract docs as routes evolve in `src/api/main.py` and `src/api/routes/judge.py`.

## Quick verification checklist
```bash
curl -s http://localhost:8050/api/health
curl -s 'http://localhost:8050/api/judge/quality?horizon_days=5&min_samples=20' | jq
openclaw channels status --probe
openclaw memory status --deep
```
