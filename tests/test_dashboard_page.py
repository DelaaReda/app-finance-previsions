import pytest

pytest.importorskip('dash.testing')


def test_dashboard_page_loads(dash_duo):
    from src.dash_app.app import app as dash_app

    dash_duo.start_server(dash_app)
    dash_duo.driver.get(dash_duo.server_url + '/dashboard')
    dash_duo.wait_for_text_to_equal('h3', 'Dashboard — Top picks', timeout=4)

