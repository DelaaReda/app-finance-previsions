import shutil
from pathlib import Path
import pandas as pd

def _write_sample_backtest():
    outdir = Path('data/backtest') / 'dt=99999999'
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    # two dates with simple realized returns
    df = pd.DataFrame([
        {'dt': '2025-01-01', 'ticker': 'AAA', 'realized_return': 0.01},
        {'dt': '2025-01-01', 'ticker': 'BBB', 'realized_return': 0.02},
        {'dt': '2025-01-02', 'ticker': 'AAA', 'realized_return': -0.005},
        {'dt': '2025-01-02', 'ticker': 'BBB', 'realized_return': 0.003},
    ])
    df.to_parquet(outdir / 'details.parquet', index=False)


def _cleanup():
    p = Path('data/backtest') / 'dt=99999999'
    if p.exists():
        shutil.rmtree(p)


def test_backtests_chart_renders():
    """Unit-style test: write a small details.parquet then call the page layout
    function directly and assert the returned layout contains a Graph with the
    expected id. This avoids dash.testing dependencies in CI while still
    verifying the rendering logic.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    from dash_app.pages import backtests

    _write_sample_backtest()
    try:
        layout = backtests.layout()
        # look for dcc.Graph by id within layout children
        found = False
        for c in getattr(layout, 'children', []):
            try:
                if getattr(c, 'id', None) == 'backtests-topn-curve':
                    found = True
                    break
            except Exception:
                continue
        assert found, 'backtests-topn-curve Graph not found in layout()'
    finally:
        _cleanup()
