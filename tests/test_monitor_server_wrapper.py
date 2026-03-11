from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import mock


WRAPPER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "monitor_server.py"


def _load_wrapper_module():
    spec = importlib.util.spec_from_file_location("fc_monitor_wrapper_test", WRAPPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_monitor_up_treats_connection_reset_as_down():
    wrapper = _load_wrapper_module()

    with mock.patch.object(
        wrapper.urllib.request,
        "urlopen",
        side_effect=ConnectionResetError(104, "Connection reset by peer"),
    ):
        assert wrapper._probe_monitor_up("http://127.0.0.1:7779/api/monitor/access") is False
