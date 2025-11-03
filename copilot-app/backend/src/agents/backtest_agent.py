"""Backtest agent

Computes a Top-N basket realized-return time series from latest forecasts and cached prices
and writes outputs under `data/backtest/dt=YYYYMMDD/`:
- details.parquet (per-date/per-ticker realized returns)
- summary.json (aggregate metrics)

Usage: PYTHONPATH=src python -m src.agents.backtest_agent --horizon 1m --top-n 5
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import argparse
import pandas as pd
import numpy as np

HORIZON_TO_DAYS = {"1w": 5, "1m": 21, "1y": 252}


def _latest_forecasts() -> pd.DataFrame:
    parts = sorted(Path('data/forecast').glob('dt=*'))
    if not parts:
        return pd.DataFrame()
    latest = parts[-1]
    # prefer forecasts.parquet then final.parquet
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


def run_backtest(horizon: str = '1m', top_n: int = 5, days_back: int = 180) -> dict:
    days = HORIZON_TO_DAYS.get(horizon, 21)
    df = _latest_forecasts()
    if df.empty:
        return {'ok': False, 'error': 'no forecasts found'}

    # ensure dt column
    if 'dt' in df.columns:
        df['dt'] = pd.to_datetime(df['dt'], errors='coerce')
    else:
        # some forecasts use 'date' or 'timestamp' — try to infer
        if 'date' in df.columns:
            df['dt'] = pd.to_datetime(df['date'], errors='coerce')
        else:
            df['dt'] = pd.Timestamp.now()

    # Work on recent window
    end = df['dt'].max()
    start = end - pd.Timedelta(days=days_back)
    df = df[(df['dt'] >= start) & (df['dt'] <= end)].copy()
    if df.empty:
        return {'ok': False, 'error': 'no forecasts in window'}

    # compute score - prefer final_score if present
    if 'final_score' in df.columns:
        df['score'] = df['final_score'].astype(float)
    else:
        dir_map = {'up': 1.0, 'flat': 0.0, 'down': -1.0}
        df['dir_base'] = df.get('direction', pd.Series()).map(dir_map).fillna(0.0)
        df['score'] = df['dir_base'] * df.get('confidence', 0.0).astype(float) + 0.5 * df.get('expected_return', 0.0).astype(float)

    details = []
    basket_returns = []

    for d, sdf in df.groupby(df['dt'].dt.date):
        sdf = sdf.sort_values('score', ascending=False).head(top_n)
        rets = []
        for _, row in sdf.iterrows():
            rr = _realized_return_for(str(row.get('ticker')), pd.Timestamp(d), days)
            if rr is None:
                continue
            rets.append(rr)
            details.append({
                'dt': str(d),
                'ticker': row.get('ticker'),
                'horizon': horizon,
                'score': float(row.get('score') or 0.0),
                'realized_return': float(rr),
            })
        if rets:
            basket_returns.append(np.mean(rets))

    # summary
    if basket_returns:
        s = pd.Series(basket_returns)
        summary = {
            'count_days': int(s.count()),
            'avg_basket_return': float(s.mean()),
            'median': float(s.median()),
            'stdev': float(s.std(ddof=1)) if len(s) > 1 else 0.0,
        }
    else:
        summary = {'count_days': 0, 'avg_basket_return': 0.0, 'median': 0.0, 'stdev': 0.0}

    outdir = Path('data/backtest') / f"dt={datetime.utcnow().strftime('%Y%m%d')}"
    outdir.mkdir(parents=True, exist_ok=True)
    if details:
        pd.DataFrame(details).to_parquet(outdir / 'details.parquet', index=False)
    (outdir / 'summary.json').write_text(json.dumps({'horizon': horizon, 'top_n': top_n, **summary}, ensure_ascii=False, indent=2), encoding='utf-8')

    return {'ok': True, **summary}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--horizon', default='1m', choices=list(HORIZON_TO_DAYS.keys()))
    p.add_argument('--top-n', type=int, default=5)
    p.add_argument('--days-back', type=int, default=180)
    args = p.parse_args()
    res = run_backtest(horizon=args.horizon, top_n=args.top_n, days_back=args.days_back)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    main()
