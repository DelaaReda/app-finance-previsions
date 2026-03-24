# ACLED Incremental Ingest Runbook

Updated: 2026-03-02

## Objective

Collect ACLED update articles as structured JSON, incremental only, and refresh 4 times per day.

## Credentials required in `apps/api/src/.env`

- `ACLED_EMAIL`
- `ACLED_PASSWORD`

## Scripts

- Ingest runner:
- `scripts/data/acled_geopolitical_ingest.py`
- Cron installer:
- `scripts/data/setup_acled_ingest_cron.sh`

## One-shot ingest

```bash
cd /home/venom/analyse-financiere
python3 scripts/data/acled_geopolitical_ingest.py
```

## 4x/day schedule (every 6 hours)

```bash
cd /home/venom/analyse-financiere
bash scripts/data/setup_acled_ingest_cron.sh enable
```

Disable:

```bash
bash scripts/data/setup_acled_ingest_cron.sh disable
```

Print crontab:

```bash
bash scripts/data/setup_acled_ingest_cron.sh print
```

## Output files

- State:
- `data/geo/acled/state.json`
- Latest snapshot:
- `data/geo/acled/latest.json`
- Articles:
- `data/geo/acled/articles/*.json`
- Run summaries:
- `data/geo/acled/runs/*.json`
- Cron logs:
- `logs/acled_ingest.log`

## Incremental behavior

- New URL: creates article JSON and state entry.
- Existing URL with unchanged hash: skipped.
- Existing URL with changed content hash: updates article JSON and state metadata.

## JSON payload (article)

- `url`
- `title`
- `published_date`
- `countries`
- `regions`
- `authors`
- `key_developments`
- `sections`
- `footnotes`
- `aspects` (war/conflict, policy/law, repression, diplomacy, supply chain, governance)
- `source_links`
- `content_hash`
