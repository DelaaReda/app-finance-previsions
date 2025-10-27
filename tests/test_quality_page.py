import pytest

pytest.importorskip('dash.testing')


def test_quality_page_loads(dash_duo):
    # Import the Dash app
    from src.dash_app.app import app as dash_app

    dash_duo.start_server(dash_app)
    # Navigate to /quality
    dash_duo.driver.get(dash_duo.server_url + '/quality')
    # Expect the title to be present or the empty-state message
    dash_duo.wait_for_text_to_equal('h3', 'Qualité des données', timeout=4)

