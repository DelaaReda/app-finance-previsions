# paths.py

Path helpers for common data artifacts.
Prefer latest dt=YYYYMMDD partition when applicable.

## Function: `p_quality_anoms`

Signature: `def p_quality_anoms(...)->Path`

Inputs:
- (none)
Returns: `Path`

## Function: `p_quality_fresh`

Signature: `def p_quality_fresh(...)->Path`

Inputs:
- (none)
Returns: `Path`

## Function: `p_agents_status`

Signature: `def p_agents_status(...)->Path`

Inputs:
- (none)
Returns: `Path`

## Function: `p_logs`

Signature: `def p_logs(...)->Path`

Inputs:
- (none)
Returns: `Path`

## Function: `p_backtests_results`

Signature: `def p_backtests_results(...)->Optional[Path]`

Latest consolidated backtests results (preferred).

Inputs:
- (none)
Returns: `Optional[Path]`

## Function: `p_backtest_details`

Signature: `def p_backtest_details(...)->Optional[Path]`

Fallback: latest partitioned backtest details.

Inputs:
- (none)
Returns: `Optional[Path]`

## Function: `p_eval_metrics_parquet`

Signature: `def p_eval_metrics_parquet(...)->Optional[Path]`

Inputs:
- (none)
Returns: `Optional[Path]`

## Function: `p_eval_metrics_json`

Signature: `def p_eval_metrics_json(...)->Optional[Path]`

Inputs:
- (none)
Returns: `Optional[Path]`

## Function: `p_eval_details`

Signature: `def p_eval_details(...)->Optional[Path]`

Inputs:
- (none)
Returns: `Optional[Path]`

## Function: `p_risk`

Signature: `def p_risk(...)->Optional[Path]`

Inputs:
- (none)
Returns: `Optional[Path]`

## Function: `p_regimes`

Signature: `def p_regimes(...)->Optional[Path]`

Inputs:
- (none)
Returns: `Optional[Path]`
