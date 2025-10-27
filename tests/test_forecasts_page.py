import pytest

pytest.importorskip('dash.testing')


def test_forecasts_page_loads(dash_duo):
    from src.dash_app.app import app as dash_app

    dash_duo.start_server(dash_app)
    dash_duo.driver.get(dash_duo.server_url + '/forecasts')
    dash_duo.wait_for_text_to_equal('h3', 'Forecasts - Prévisions Multi-Actifs', timeout=4)
    # forecasts-content container should exist
    dash_duo.wait_for_element('#forecasts-content', timeout=4)

