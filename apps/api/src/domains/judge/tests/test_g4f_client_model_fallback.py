from __future__ import annotations

import json
from pathlib import Path

from services import g4f_client


def test_ranked_models_prefers_working_json(monkeypatch, tmp_path: Path):
    backend_root = tmp_path / "backend"
    src_root = backend_root / "src"
    working_dir = backend_root / "data" / "llm" / "models"
    working_dir.mkdir(parents=True, exist_ok=True)
    src_root.mkdir(parents=True, exist_ok=True)

    (working_dir / "working.json").write_text(
        json.dumps(
            {
                "asof": "2026-02-27T00:00:00Z",
                "models": [
                    {"model": "deepseek-ai/DeepSeek-V3", "ok": True, "provider": "DeepInfra", "pass_rate": 0.95, "latency_s": 2.4, "source": "verified"},
                    {"model": "qwen/qwen3-235b-a22b", "ok": True, "provider": "DeepInfra", "pass_rate": 0.92, "latency_s": 2.9, "source": "verified"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (src_root / "tested_g4f_models_ok.json").write_text(
        json.dumps(
            [
                {"provider": "AnyProvider", "model": "command-a", "ok": True, "ms": 250.0, "answer": "OK", "category": "helper_json"},
                {"provider": "Perplexity", "model": "pplx_pro_upgraded", "ok": True, "ms": 1000.0, "answer": "OK", "category": "forecast"},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(g4f_client, "_backend_root", lambda: backend_root)
    monkeypatch.setattr(g4f_client, "_src_root", lambda: src_root)

    ranked = g4f_client.get_ranked_tested_models(category_preference="forecast", limit=4)
    assert ranked, "Expected non-empty ranked tested model list."
    assert ranked[0][1] == "deepseek-ai/DeepSeek-V3"


def test_ranked_models_cache_invalidates_when_working_file_changes(monkeypatch, tmp_path: Path):
    backend_root = tmp_path / "backend"
    src_root = backend_root / "src"
    working_dir = backend_root / "data" / "llm" / "models"
    working_dir.mkdir(parents=True, exist_ok=True)
    src_root.mkdir(parents=True, exist_ok=True)

    working_path = working_dir / "working.json"
    working_path.write_text(
        json.dumps(
            {
                "asof": "2026-02-27T00:00:00Z",
                "models": [
                    {"model": "deepseek-ai/DeepSeek-V3", "ok": True, "provider": "DeepInfra", "pass_rate": 0.95, "latency_s": 2.4, "source": "verified"},
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(g4f_client, "_backend_root", lambda: backend_root)
    monkeypatch.setattr(g4f_client, "_src_root", lambda: src_root)
    monkeypatch.setattr(g4f_client, "_RANKED_MODELS_CACHE", {})
    monkeypatch.setattr(g4f_client, "_RANKED_MODELS_CACHE_TTL_SECONDS", 9999.0)

    first = g4f_client.get_ranked_tested_models(category_preference="forecast", limit=2)
    assert first and first[0][1] == "deepseek-ai/DeepSeek-V3"

    working_path.write_text(
        json.dumps(
            {
                "asof": "2026-02-27T00:10:00Z",
                "models": [
                    {"model": "qwen/qwen3-235b-a22b", "ok": True, "provider": "DeepInfra", "pass_rate": 0.93, "latency_s": 2.1, "source": "verified"},
                ],
            }
        ),
        encoding="utf-8",
    )

    second = g4f_client.get_ranked_tested_models(category_preference="forecast", limit=2)
    assert second and second[0][1] == "qwen/qwen3-235b-a22b"


def test_call_g4f_falls_back_to_next_candidate(monkeypatch):
    class _FakeResponse:
        def __init__(self, content: str):
            self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})]

        def model_dump_json(self) -> str:
            return json.dumps({"ok": True})

    class _FakeCompletions:
        def create(self, **kwargs):
            model = kwargs.get("model")
            if model == "model-fail":
                raise RuntimeError("forced failure")
            return _FakeResponse("fallback_success")

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self):
            self.chat = _FakeChat()

    monkeypatch.setattr(g4f_client, "G4FClient", _FakeClient)
    monkeypatch.setattr(g4f_client, "get_llm_settings", None)
    monkeypatch.delenv("G4F_MODEL", raising=False)
    monkeypatch.delenv("G4F_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_DEFAULT_MODEL", raising=False)
    monkeypatch.setattr(
        g4f_client,
        "get_ranked_tested_models",
        lambda category_preference="forecast", limit=12: [
            ("DeepInfra", "model-fail"),
            ("DeepInfra", "model-ok"),
        ],
    )

    result = g4f_client.call_g4f(
        messages=[{"role": "user", "content": "ping"}],
        model="model-fail",
        provider="DeepInfra",
        timeout=10,
    )
    assert result.get("ok") is True
    assert result.get("model") == "model-ok"
    assert result.get("answer") == "fallback_success"
    attempted = result.get("attempted") or []
    assert attempted and attempted[0].get("model") == "model-fail"


def test_get_mode_model_candidates_dev_prefers_dev_models(monkeypatch):
    monkeypatch.setenv("LLM_DEV_MODELS", "fast-a,fast-b")
    monkeypatch.setattr(
        g4f_client,
        "get_ranked_tested_models",
        lambda category_preference="forecast", limit=12: [
            ("ProviderX", "ranked-1"),
            ("ProviderY", "ranked-2"),
        ],
    )
    candidates = g4f_client.get_mode_model_candidates(mode="dev", category_preference="forecast", limit=5)
    assert candidates[:2] == [(None, "fast-a"), (None, "fast-b")]


def test_get_mode_model_candidates_fastest_prefers_fastest_models(monkeypatch):
    monkeypatch.setenv("LLM_FASTEST_MODELS", "fastest-a,fastest-b")
    monkeypatch.setattr(
        g4f_client,
        "_working_fast_pairs",
        lambda category_preference="forecast", include_low_confidence=True: [("ProviderX", "ranked-fast-1")],
    )
    monkeypatch.setattr(
        g4f_client,
        "_categorized_tested_pairs",
        lambda category_preference="forecast": [("ProviderY", "ranked-fast-2")],
    )
    monkeypatch.setattr(
        g4f_client,
        "_flat_tested_pairs",
        lambda category_preference="forecast": [],
    )
    monkeypatch.setattr(
        g4f_client,
        "get_ranked_tested_models",
        lambda category_preference="forecast", limit=12: [("ProviderZ", "ranked-best-fallback")],
    )
    candidates = g4f_client.get_mode_model_candidates(mode="fastest", category_preference="forecast", limit=6)
    assert candidates[:2] == [(None, "fastest-a"), (None, "fastest-b")]
    assert ("ProviderX", "ranked-fast-1") in candidates


def test_call_llm_applies_dev_mode_timeout_and_attempts(monkeypatch):
    captured = {}

    def _fake_call_g4f(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "answer": "ok", "model": "fast-a", "provider": None}

    monkeypatch.setenv("LLM_DEV_TIMEOUT_SECONDS", "11")
    monkeypatch.setenv("LLM_DEV_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("LLM_DEV_MODELS", "fast-a")
    monkeypatch.setattr(g4f_client, "call_g4f", _fake_call_g4f)
    monkeypatch.setattr(
        g4f_client,
        "get_ranked_tested_models",
        lambda category_preference="forecast", limit=12: [],
    )

    result = g4f_client.call_llm(
        messages=[{"role": "user", "content": "ping"}],
        mode="dev",
        category_preference="forecast",
    )

    assert result.get("ok") is True
    assert captured.get("timeout") == 11
    assert captured.get("max_attempts") == 2
    assert captured.get("llm_mode") == "dev"


def test_call_llm_applies_fastest_timeout_and_attempts(monkeypatch):
    captured = {}

    def _fake_call_g4f(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "answer": "ok", "model": "fastest-a", "provider": None}

    monkeypatch.setenv("LLM_FASTEST_TIMEOUT_SECONDS", "9")
    monkeypatch.setenv("LLM_FASTEST_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("LLM_FASTEST_MODELS", "fastest-a")
    monkeypatch.setattr(g4f_client, "call_g4f", _fake_call_g4f)
    monkeypatch.setattr(
        g4f_client,
        "_working_fast_pairs",
        lambda category_preference="forecast", include_low_confidence=True: [],
    )
    monkeypatch.setattr(
        g4f_client,
        "_categorized_tested_pairs",
        lambda category_preference="forecast": [],
    )
    monkeypatch.setattr(
        g4f_client,
        "_flat_tested_pairs",
        lambda category_preference="forecast": [],
    )
    monkeypatch.setattr(
        g4f_client,
        "get_ranked_tested_models",
        lambda category_preference="forecast", limit=12: [],
    )

    result = g4f_client.call_llm(
        messages=[{"role": "user", "content": "ping"}],
        mode="fastest",
        category_preference="forecast",
    )

    assert result.get("ok") is True
    assert captured.get("timeout") == 9
    assert captured.get("max_attempts") == 1
    assert captured.get("llm_mode") == "fastest"
