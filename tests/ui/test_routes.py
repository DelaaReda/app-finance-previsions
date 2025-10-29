import pytest
from dash.testing.application_runners import import_app


@pytest.mark.parametrize(
    "route",
    [
        "/",
        "/dashboard",
        "/forecasts",
        "/regimes",
        "/risk",
        "/recession",
        "/agents",
        "/observability",
        "/news",
        "/integration_overview",
        "/integration_agents_health",
        "/integration_deep_snapshot",
    ],
)
def test_routes_200(dash_duo, route):
    app = import_app("src.dash_app.app")
    dash_duo.start_server(app)
    dash_duo.driver.get(dash_duo.server_url + route)
    assert dash_duo.get_logs() == []
