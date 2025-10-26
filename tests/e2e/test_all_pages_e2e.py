"""E2E test: visit all registered Dash pages and assert they render.

These tests require dash[testing], a working browser driver (chromedriver)
and must be enabled with ENABLE_DASH_E2E=1 to run locally/CI.
"""
import os
import sys
import pytest
from pathlib import Path

pytest.importorskip('dash.testing')


@pytest.mark.skipif(os.getenv('ENABLE_DASH_E2E') != '1', reason='Enable E2E with ENABLE_DASH_E2E=1')
def test_all_pages_render(dash_duo):
    # ensure app package importable
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    import dash_app.app as app_module
    app = app_module.app

    dash_duo.start_server(app)
    server = dash_duo.server_url
    print('E2E: server_url=', server)

    pages = list(app_module._page_registry().keys())
    failures = []

    # simple heuristics: for known route name fragments expect specific element ids
    heuristics = {
        'backtest': ['#backtests-topn-curve', '#backtests-charts'],
        'evaluation': ['#evaluation-table'],
        'forecast': ['#forecasts-table'],
        'forecasts': ['#forecasts-table'],
        'dashboard': ['#dash-top-final'],
        'agents': ['#global-status-badge'],
        'observability': ['#page-content'],
    }

    for path in pages:
        try:
            full = server + path
            dash_duo.wait_for_page(full)
            # wait for the main container to appear
            dash_duo.wait_for_element('#page-content', timeout=5)

            # choose expected selectors based on heuristics
            expected = None
            for key, sels in heuristics.items():
                if key in path:
                    expected = sels
                    break

            if expected is None:
                # fallback: ensure page-content has some text
                body_text = dash_duo.find_element('body').text
                if not body_text or body_text.strip() == '':
                    failures.append((path, 'empty body'))
                continue

            # check each selector in expected list
            for sel in expected:
                try:
                    dash_duo.wait_for_element(sel, timeout=3)
                except Exception:
                    failures.append((path, f'missing selector {sel}'))
        except Exception as e:
            failures.append((path, repr(e)))

    if failures:
        msgs = '\n'.join([f"{p}: {m}" for p, m in failures])
        pytest.fail(f"Some pages failed to render or missed expected elements:\n{msgs}")
