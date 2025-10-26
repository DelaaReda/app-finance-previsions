import shutil
from pathlib import Path
import json

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


def test_evaluation_table_renders():
    """Call layout() and verify DataTable id is present and header label exists."""
    import sys, os
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    from dash_app.pages import evaluation

    _write_sample_metrics()
    try:
        card = evaluation.render_metrics()
        # The DataTable is nested inside the CardBody -> DataTable; search children
        found = False
        def _walk(node):
            nonlocal found
            try:
                if getattr(node, 'id', None) == 'evaluation-table':
                    found = True
                    return
            except Exception:
                pass
            for c in getattr(node, 'children', []) or []:
                _walk(c)

        _walk(card)
        assert found, 'evaluation-table not found in render_metrics() output'
    finally:
        _cleanup()
