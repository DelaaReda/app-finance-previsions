import pytest

pytest.importorskip('dash.testing')


def test_agents_status_page_loads(dash_duo):
    from src.dash_app.app import app as dash_app

    dash_duo.start_server(dash_app)
    dash_duo.driver.get(dash_duo.server_url + '/agents')
    dash_duo.wait_for_text_to_equal('h3', 'Agents Status', timeout=4)

