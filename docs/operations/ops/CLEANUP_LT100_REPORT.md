# Cleanup LT100 Report

Timestamp UTC: 20260228T005817Z
Root cleaned: /home/venom/analyse-financiere/copilot-app/src
Archive backup: /home/venom/analyse-financiere/archive/cleanup_lt100_20260228T005817Z
Scanned text files: 801
Moved LT100: 451
Kept GTE100: 350
Manifest path: /home/venom/analyse-financiere/archive/cleanup_lt100_20260228T005817Z/manifest.json

Excluded directories:
- .cache
- .git
- .mypy_cache
- .next
- .pytest_cache
- .ruff_cache
- .venv
- __pycache__
- build
- dist
- node_modules

Sample moved files:
- backend/.codacy/.gitignore (6 lines)
- backend/.codacy/cli-config.yaml (1 lines)
- backend/.codacy/codacy.yaml (16 lines)
- backend/.codacy/tools-configs/eslint.config.mjs (67 lines)
- backend/.codacy/tools-configs/languages-config.yaml (34 lines)
- backend/.codacy/tools-configs/lizard.yaml (51 lines)
- backend/.codacy/tools-configs/pylint.rc (10 lines)
- backend/.codacy/tools-configs/revive.toml (57 lines)
- backend/.codacy/tools-configs/trivy.yaml (11 lines)
- backend/.qwen_runs/20251211-233159/marker.txt (3 lines)
- backend/.qwen_runs/20251212-001810/marker.txt (3 lines)
- backend/.qwen_runs/20260223-102010-879/marker.txt (3 lines)
- backend/README.md (91 lines)
- backend/api.log (0 lines)
- backend/data/alerts/rules.json (63 lines)
- backend/data/alerts.json (18 lines)
- backend/data/backtests.json (27 lines)
- backend/data/brief_daily.json (80 lines)
- backend/data/brief_weekly.json (78 lines)
- backend/data/dashboard_kpis.json (65 lines)
- backend/data/forecast/dt=20251105/final.parquet (13 lines)
- backend/data/forecast/dt=20251105/forecasts.parquet (12 lines)
- backend/data/forecasts_all_all_all_1_0_score_desc.json (49 lines)
- backend/data/forecasts_all_all_all_2_0_score_desc.json (67 lines)
- backend/data/forecasts_all_all_all_3_0_score_desc.json (85 lines)
- backend/data/forecasts_equity_1w_all_1_0_score_desc.json (49 lines)
- backend/data/forecasts_equity_1w_all_3_0_score_desc.json (85 lines)
- backend/data/forecasts_short_all_12.json (26 lines)
- backend/data/intelligence_snapshot.json (54 lines)
- backend/data/judge_profiles/equity_1w.yaml (24 lines)
- backend/data/judge_profiles/sector_regime.yaml (27 lines)
- backend/data/judge_quality_tracking.json (85 lines)
- backend/data/judge_verdicts_20_0.5_all_confidence_desc.json (41 lines)
- backend/data/llm_judge.json (98 lines)
- backend/data/market_context_snapshot.json (29 lines)
- backend/data/prediction_accuracy.json (45 lines)
- backend/data/price_cache/stooq/BRK.B.csv (1 lines)
- backend/data/quality/reports/quality_report_20260227_132843_8561e34e.json (41 lines)
- backend/data/rag/facts.jsonl (0 lines)
- backend/data/rag/news.jsonl (2 lines)
- backend/data/recommendations_daily_default_3.json (53 lines)
- backend/data/stocks/portfolio_allocation.json (20 lines)
- backend/data/test/nested/path.json (1 lines)
- backend/data/test_cache_key.json (2 lines)
- backend/data/test_cache_key2.json (11 lines)
- backend/data/user_portfolios.json (14 lines)
- backend/docs/2025-12/JUDGE_SCHEMA.md (90 lines)
- backend/jobs/__init__.py (0 lines)
- backend/jobs/alerts.py (7 lines)
- backend/jobs/backtests.py (7 lines)
- backend/jobs/backtests_job.py (7 lines)
- backend/jobs/backtests_simple.py (7 lines)
- backend/jobs/cache_manager.py (7 lines)
- backend/jobs/calendar_ingest.py (7 lines)
- backend/jobs/capital_flow.py (7 lines)
- backend/jobs/correlation_calculator.py (7 lines)
- backend/jobs/dashboard_refresh.py (7 lines)
- backend/jobs/data_quality_gate.py (7 lines)
- backend/jobs/data_seeder.py (7 lines)
- backend/jobs/efficient_frontier.py (7 lines)
- ... and 391 more (see manifest)
