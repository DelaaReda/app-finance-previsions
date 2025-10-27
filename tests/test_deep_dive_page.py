import pytest

pytest.importorskip('dash.testing')


def test_deep_dive_page_input_exists(dash_duo):
    from src.dash_app.app import app as dash_app

    dash_duo.start_server(dash_app)
    dash_duo.driver.get(dash_duo.server_url + '/deep_dive')
    dash_duo.wait_for_text_to_equal('h3', "Deep Dive - Analyse d'un titre", timeout=4)
    # input exists
    dash_duo.wait_for_element('#deep-dive-ticker', timeout=4)

