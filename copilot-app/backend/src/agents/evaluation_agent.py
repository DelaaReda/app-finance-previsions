"""Evaluation agent

Computes MAE, RMSE and hit ratio for forecasts by agent/provider (if available) or overall.
Writes outputs under `data/evaluation/dt=YYYYMMDD/` as `metrics.json` and `details.parquet`.

Usage: PYTHONPATH=src python -m src.agents.evaluation_agent --horizon 1m --top-n 5
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import argparse
import math
import pandas as pd
import numpy as np

HORIZON_TO_DAYS = {"1w": 5, "1m": 21, "1y": 252}


def _latest_forecasts() -> pd.DataFrame:
    parts = sorted(Path('data/forecast').glob('dt=*'))
    if not parts:
        return pd.DataFrame()
    latest = parts[-1]
    f1 = latest / 'forecasts.parquet'
    f2 = latest / 'final.parquet'
    if f1.exists():
        return pd.read_parquet(f1)
    if f2.exists():
        return pd.read_parquet(f2)
    return pd.DataFrame()


def _cached_prices(ticker: str) -> pd.DataFrame | None:
    p = Path('data/prices') / f'ticker={ticker}' / 'prices.parquet'
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.set_index('date').sort_index()
        return df
    except Exception:
        return None


def _realized_return_for(ticker: str, dt: pd.Timestamp, days: int) -> float | None:
    dfp = _cached_prices(ticker)
    if dfp is None or dfp.empty:
        return None
    if 'Close' in dfp.columns:
        price_col = 'Close'
    elif 'close' in dfp.columns:
        price_col = 'close'
    else:
        return None
    try:
        idx = dfp.index.get_loc(dt, method='nearest')
    except Exception:
        after = dfp[dfp.index >= dt]
        if after.empty:
            return None
        idx = dfp.index.get_loc(after.index[0])
    j = min(len(dfp) - 1, idx + days)
    try:
        r = float(dfp[price_col].iloc[j] / dfp[price_col].iloc[idx] - 1.0)
        return r
    except Exception:
        return None


def compute_metrics(horizon: str = '1m', days_back: int = 180) -> dict:
    days = HORIZON_TO_DAYS.get(horizon, 21)
    df = _latest_forecasts()
    if df.empty:
        return {'ok': False, 'error': 'no forecasts found'}

    if 'dt' in df.columns:
        df['dt'] = pd.to_datetime(df['dt'], errors='coerce')
    else:
        if 'date' in df.columns:
            df['dt'] = pd.to_datetime(df['date'], errors='coerce')
        else:
            df['dt'] = pd.Timestamp.now()

    end = df['dt'].max()
    start = end - pd.Timedelta(days=days_back)
    df = df[(df['dt'] >= start) & (df['dt'] <= end)].copy()
    if df.empty:
        return {'ok': False, 'error': 'no forecasts in window'}

    # Compute realized returns for each row if possible
    realized = []
    for idx, row in df.iterrows():
        ticker = str(row.get('ticker'))
        dt = pd.Timestamp(row.get('dt'))
        rr = _realized_return_for(ticker, dt, days)
        realized.append(rr)
    df['realized_return'] = realized

    # Determine grouping key (provider/agent/source) if present
    if 'provider' in df.columns:
        group_key = 'provider'
    elif 'agent' in df.columns:
        group_key = 'agent'
    elif 'source' in df.columns:
        group_key = 'source'
    else:
        group_key = None

    results = {}

    def _metrics_for(sub: pd.DataFrame) -> dict:
        sub = sub.dropna(subset=['realized_return'])
        if sub.empty:
            return {'count': 0, 'mae': None, 'rmse': None, 'hit_ratio': None}
        # expected value: try 'expected_return' then 'expected' else 0
        if 'expected_return' in sub.columns:
            exp = sub['expected_return'].astype(float).fillna(0.0)
        else:
            exp = pd.Series([0.0] * len(sub))
        err = sub['realized_return'].astype(float) - exp
        mae = float(err.abs().mean())
        rmse = float((err ** 2).mean() ** 0.5)
        # hit ratio: sign match between expected and realized (or direction vs realized)
        if 'direction' in sub.columns:
            dir_map = {'up': 1.0, 'down': -1.0, 'flat': 0.0}
            pred_dir = sub['direction'].map(dir_map).fillna(0.0)
            hits = (np.sign(sub['realized_return'].astype(float)) == np.sign(pred_dir)).sum()
            hit_ratio = float(hits) / float(len(sub))
        else:
            hits = (np.sign(sub['realized_return'].astype(float)) == np.sign(exp)).sum()
            hit_ratio = float(hits) / float(len(sub))
        return {'count': int(len(sub)), 'mae': mae, 'rmse': rmse, 'hit_ratio': hit_ratio}

    if group_key:
        for k, sub in df.groupby(df[group_key].fillna('unknown')):
            results[str(k)] = _metrics_for(sub)
    else:
        results['all'] = _metrics_for(df)

    # Write outputs
    outdir = Path('data/evaluation') / f"dt={datetime.utcnow().strftime('%Y%m%d')}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'metrics.json').write_text(json.dumps({'horizon': horizon, 'by': group_key, 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    try:
        df.to_parquet(outdir / 'details.parquet', index=False)
    except Exception:
        pass

    return {'ok': True, 'by': group_key, 'groups': len(results)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--horizon', default='1m', choices=list(HORIZON_TO_DAYS.keys()))
    p.add_argument('--days-back', type=int, default=180)
    args = p.parse_args()
    res = compute_metrics(horizon=args.horizon, days_back=args.days_back)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    main()
