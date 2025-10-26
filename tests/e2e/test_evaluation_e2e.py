import os
import sys
import shutil
from pathlib import Path
import json
import pytest

pytest.importorskip('dash.testing')


def _write_sample_metrics():
    outdir = Path('data/evaluation') / 'dt=99999999'
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    metrics = {
        'by': None,
        'results': {
            'all': {'count': 2, 'mae': 0.0123, 'rmse': 0.0156, 'hit_ratio': 0.5}
        }
    }
    (outdir / 'metrics.json').write_text(json.dumps(metrics), encoding='utf-8')


def _cleanup():
    p = Path('data/evaluation') / 'dt=99999999'
    if p.exists():
        shutil.rmtree(p)


@pytest.mark.skipif(os.getenv('ENABLE_DASH_E2E') != '1', reason='Enable with ENABLE_DASH_E2E=1')
def test_evaluation_table_renders_e2e(dash_duo):
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    from dash_app.app import app

    _write_sample_metrics()
    try:
        dash_duo.start_server(app)
        full_url = dash_duo.server_url + '/evaluation'
        print('E2E: server_url=', dash_duo.server_url)
        dash_duo.wait_for_page(full_url)
        dash_duo.wait_for_element('#evaluation-table', timeout=5)
        assert dash_duo.find_element('#evaluation-table') is not None
    finally:
        _cleanup()
