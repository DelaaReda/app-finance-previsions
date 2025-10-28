import os
import sys
import pytest

pytest.importorskip('dash.testing')


@pytest.mark.skipif(os.getenv('ENABLE_DASH_E2E') != '1', reason='Enable with ENABLE_DASH_E2E=1')
def test_risk_regimes_render(dash_duo):
    # Ensure app import path
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    from dash_app.app import app

    dash_duo.start_server(app)

    # Risk
    dash_duo.wait_for_page(dash_duo.server_url + '/risk')
    dash_duo.wait_for_element('#risk-body', timeout=5)

    # Regimes
    dash_duo.wait_for_page(dash_duo.server_url + '/regimes')
    dash_duo.wait_for_element('#regimes-body', timeout=5)

