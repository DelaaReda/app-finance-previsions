import pytest

pytest.importorskip('dash.testing')


def test_signals_page_has_table(dash_duo):
    from src.dash_app.app import app as dash_app

    dash_duo.start_server(dash_duo)  # ensure server fixture init
    dash_duo.start_server(dash_app)
    dash_duo.driver.get(dash_duo.server_url + '/signals')
    dash_duo.wait_for_text_to_equal('h3', 'Signals', timeout=4)
    # DataTable with id signals-table should exist (even if empty)
    dash_duo.wait_for_element('#signals-table', timeout=4)

