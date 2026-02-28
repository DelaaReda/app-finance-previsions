from __future__ import annotations

from src.services import correlation_service, dashboard_service, flows_service


def test_dashboard_service_unwraps_data_wrapper(monkeypatch):
    monkeypatch.setattr(dashboard_service, "load_json", lambda _key: {"data": {"kpi": 1}})
    assert dashboard_service.get_dashboard_kpis() == {"kpi": 1}


def test_flows_service_unwraps_payload_wrapper(monkeypatch):
    monkeypatch.setattr(flows_service, "load_json", lambda _key: {"payload": {"nodes": ["a"], "links": []}})
    payload = flows_service.get_capital_flows()
    assert payload["nodes"] == ["a"]
    assert payload["links"] == []


def test_correlation_service_network_threshold_filter_does_not_mutate_source(monkeypatch):
    source = {
        "payload": {
            "nodes": [{"id": "A"}],
            "links": [{"correlation": 0.2}, {"correlation": 0.8}],
            "threshold": 0.1,
        }
    }
    monkeypatch.setattr(correlation_service, "load_json", lambda _key: source)

    filtered = correlation_service.get_correlation_network(threshold=0.5)
    assert filtered["threshold"] == 0.5
    assert len(filtered["links"]) == 1
    assert source["payload"]["threshold"] == 0.1


def test_correlation_service_matrix_fallback_includes_generated_at(monkeypatch):
    def _raise(_key):
        raise RuntimeError("boom")

    monkeypatch.setattr(correlation_service, "load_json", _raise)
    payload = correlation_service.get_correlation_matrix()
    assert payload["matrix"] == {}
    assert payload["tickers"] == []
    assert payload["generated_at"].endswith("Z")
