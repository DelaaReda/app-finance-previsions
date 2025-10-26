import os
import sys
import shutil
from pathlib import Path
import pandas as pd
import pytest

pytest.importorskip('dash.testing')


def _write_sample_backtest():
    outdir = Path('data/backtest') / 'dt=99999999'
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([
        {'dt': '2025-01-01', 'ticker': 'AAA', 'realized_return': 0.01},
        {'dt': '2025-01-01', 'ticker': 'BBB', 'realized_return': 0.02},
    ])
    df.to_parquet(outdir / 'details.parquet', index=False)


def _cleanup():
    p = Path('data/backtest') / 'dt=99999999'
    if p.exists():
        shutil.rmtree(p)


@pytest.mark.skipif(os.getenv('ENABLE_DASH_E2E') != '1', reason='Enable with ENABLE_DASH_E2E=1')
def test_backtests_chart_renders_e2e(dash_duo):
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    from dash_app.app import app

    _write_sample_backtest()
    try:
        dash_duo.start_server(app)
        # use full URL to avoid passing a relative path to selenium
        full_url = dash_duo.server_url + '/backtests'
        print('E2E: server_url=', dash_duo.server_url)
        dash_duo.wait_for_page(full_url)
        dash_duo.wait_for_element('#backtests-topn-curve', timeout=5)
        assert dash_duo.find_element('.js-plotly-plot') is not None
    finally:
        _cleanup()
