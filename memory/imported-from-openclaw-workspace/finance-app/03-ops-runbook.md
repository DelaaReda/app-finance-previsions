# Finance App Ops Runbook

Updated: 2026-02-24

## Start/stop/restart
```bash
cd /Users/venom/Documents/analyse-financiere
./finance-copilot.sh restart
./finance-copilot.sh stop
```

## Manual backend jobs (inside backend dir)
```bash
cd /Users/venom/Documents/analyse-financiere/copilot-app/backend
PYTHONPATH=src:. .venv/bin/python jobs/news_ingest.py
PYTHONPATH=src:. .venv/bin/python jobs/news_sentiment.py
PYTHONPATH=src:. .venv/bin/python jobs/macro_series_snapshot.py
PYTHONPATH=src:. .venv/bin/python jobs/stocks_prices_refresh.py --force --timeframe 1y
PYTHONPATH=src:. .venv/bin/python jobs/judge_enrich.py
PYTHONPATH=src:. .venv/bin/python jobs/judge_quality_report.py
```

## Price source fallback
- Stooq script:
```bash
/Users/venom/Documents/analyse-financiere/copilot-app/backend/scripts/fetch_prices_stooq.sh
```

## Judge quality check
```bash
curl -s 'http://localhost:8050/api/judge/quality?horizon_days=5&min_samples=20' | jq
```

## Common pitfalls
- Wrong working directory causes path errors (example: duplicated `copilot-app/copilot-app/...`).
- Missing virtualenv interpreter causes `no such file or directory: .venv/bin/python`.
- Run from backend directory when invoking backend jobs.

## Observability
- Backend log file: `/Users/venom/Documents/analyse-financiere/copilot-app/backend/api.log`
- Sentry route for validation (debug mode): `GET /sentry-debug`
