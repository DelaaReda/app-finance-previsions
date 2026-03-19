"""Copilot ask payload tests."""

import asyncio
import json
import urllib.request
from typing import Any, Dict, List, Optional

import pytest

from domains.copilot.application import copilot_service
from storage import io as storage_io


class _FakeContextService:
    async def get_current_market_context(self) -> Dict[str, Any]:
        return {
            "regime": "BULL_MARKET",
            "confidence": 0.73,
            "key_drivers": ["vix bas", "news positives"],
            "characteristics": {
                "volatility": "low",
                "sentiment": "bullish",
            },
            "metadata": {
                "generated_at": "2026-03-02T21:00:00Z",
                "sources": ["forecasts", "macro", "news"],
            },
            "recommended_layout": {
                "primary_widgets": ["ForecastCardsWidget"],
            },
        }


class _FakeRAGStore:
    def __init__(self) -> None:
        self.search_calls: List[Dict[str, Any]] = []

    def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10):
        self.search_calls.append({"scope": scope or {}, "top_k": top_k})
        return [
            {
                "text": "NVDA Q4 guidance beat expectations",
                "meta": {"type": "news", "ticker": "NVDA", "url": "https://example.com/nvda", "date": "2026-03-01"},
                "id": "n1",
            },
            {
                "text": "CPI stable at annualized 2.1%",
                "meta": {"type": "series", "url": "", "date": "2026-03-01"},
                "id": "c1",
            },
        ]


def test_ask_payload_injects_market_context_and_structured_response():
    fake_rag = _FakeRAGStore()

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert "Contexte marché auto" in question
        assert len(context_chunks) == 2
        return {
            "model": "test-llm",
            "answer": json.dumps(
                {
                    "action": "buy",
                    "reasoning": [
                        "Analyse macro favorable",
                        "Momentum haussier",
                        "Risque limité par volatilité plus faible",
                    ],
                }
            ),
            "citations": [],
        }

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Que faire aujourd'hui ?",
            tickers=["NVDA"],
            max_sources=2,
            rag_store_cls=lambda: fake_rag,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FakeContextService,
        )
    )
    assert response.get("action") == "buy"
    assert response.get("verdict") == "buy"
    assert response.get("why") == response.get("reasoning")
    assert response.get("risk", {}).get("level") in {"low", "medium", "high", "critical"}
    assert isinstance(response.get("risk", {}).get("caveat"), str)
    assert response.get("risk_caveat") == "Contexte marché et sources disponibles."
    assert response.get("sources_count") == 2
    assert response["requirements_met"]["min_sources_2"] is True
    assert response["quality_status"] == "sufficient_sources"
    assert len(response.get("reasoning", [])) == 3
    assert response["memo"]["verdict"] == "buy"
    assert response["memo"]["horizon"] == "1w"
    assert response["memo"]["why"] == response["why"]
    assert response["memo"]["risks"][-1] == response["risk_caveat"]
    assert response["memo"]["confidence"] == response["confidence"]
    assert response["memo"]["freshness"] == response["freshness"]
    assert response["memo"]["sources"] == response["sources"]


def test_ask_payload_uses_market_context_when_rag_empty():
    class _EmptyRAGStore(_FakeRAGStore):
        def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10):
            return []

    fake_rag = _EmptyRAGStore()

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert any(chunk.get("meta", {}).get("type") == "market_context" for chunk in context_chunks)
        assert "Contexte marché auto" in question
        return {"model": "test-llm", "answer": "Je recommande de HOLD sur AAPL pour le moment.", "citations": []}

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Quelle action recommandez-vous pour le portefeuille ?",
            tickers=["AAPL"],
            max_sources=2,
            rag_store_cls=lambda: fake_rag,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FakeContextService,
        )
    )

    assert response.get("action") == "hold"
    assert response.get("verdict") == "hold"
    assert response.get("why")
    assert response.get("risk", {}).get("level") in {"low", "medium", "high", "critical"}
    assert response.get("sources_count") == 1
    assert response["quality_status"] == "insufficient_sources"
    assert response["requirements_met"]["min_sources_2"] is False
    assert response.get("answer").startswith("Je recommande")
    assert len(response.get("reasoning", [])) >= 1


def test_ask_payload_fallback_when_market_context_service_fails():
    class _FailingContextService:
        async def get_current_market_context(self) -> Dict[str, Any]:
            raise RuntimeError("service indisponible")

    class _EmptyRAGStore:
        def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10):
            return []

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert any(chunk.get("meta", {}).get("type") == "market_context" for chunk in context_chunks)
        assert "Contexte marché auto" in question
        return {"model": "test-llm", "answer": "Je recommande HOLD sur AAPL.", "citations": []}

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Analyse AAPL en profondeur",
            tickers=["AAPL"],
            max_sources=2,
            rag_store_cls=_EmptyRAGStore,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FailingContextService,
        )
    )

    assert response.get("action") == "hold"
    assert response.get("verdict") == "hold"
    assert response.get("why")
    assert response.get("risk", {}).get("level") in {"low", "medium", "high", "critical"}
    assert response.get("sources_count") == 1
    assert response["quality_status"] == "insufficient_sources"
    assert response["requirements_met"]["min_sources_2"] is False


def test_ask_payload_uses_structured_confidence_when_sources_are_sufficient():
    fake_rag = _FakeRAGStore()

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert len(context_chunks) == 2
        return {
            "model": "test-llm",
            "answer": json.dumps(
                {
                    "action": "buy",
                    "confidence": 67,
                    "reasoning": [
                        "Momentum reste favorable",
                        "Le contexte macro n'est pas deterioré",
                        "Les risques sont identifiés mais contenus",
                    ],
                }
            ),
            "citations": [],
        }

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Donne-moi un memo d'investissement sur NVDA.",
            tickers=["NVDA"],
            max_sources=2,
            rag_store_cls=lambda: fake_rag,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FakeContextService,
        )
    )

    assert response["quality_status"] == "sufficient_sources"
    assert response["requirements_met"]["min_sources_2"] is True
    assert response["confidence"] == 0.67
    assert response["freshness"] == response["generated_at"]


def test_ask_payload_preserves_structured_memo_fields():
    fake_rag = _FakeRAGStore()

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert len(context_chunks) == 2
        return {
            "model": "test-llm",
            "answer": json.dumps(
                {
                    "action": "buy",
                    "horizon": "3m",
                    "why": [
                        "Earnings revisions stay positive",
                        "Sector breadth keeps improving",
                    ],
                    "risks": [
                        "Valuation is already demanding",
                        "Macro surprises could compress multiples",
                    ],
                    "next_steps": [
                        "Wait for the next CPI release",
                    ],
                    "invalidation": [
                        "Break below the prior earnings gap",
                    ],
                    "confidence": 0.64,
                }
            ),
            "citations": [],
        }

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Build an investment memo for NVDA.",
            tickers=["NVDA"],
            max_sources=2,
            rag_store_cls=lambda: fake_rag,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FakeContextService,
        )
    )

    assert response["horizon"] == "3m"
    assert response["why"] == [
        "Earnings revisions stay positive",
        "Sector breadth keeps improving",
    ]
    assert response["risks"] == [
        "Valuation is already demanding",
        "Macro surprises could compress multiples",
    ]
    assert response["next_steps"] == ["Wait for the next CPI release"]
    assert response["invalidation"] == ["Break below the prior earnings gap"]
    assert response["memo"] == {
        "verdict": "buy",
        "horizon": "3m",
        "why": [
            "Earnings revisions stay positive",
            "Sector breadth keeps improving",
        ],
        "risks": [
            "Valuation is already demanding",
            "Macro surprises could compress multiples",
        ],
        "confidence": 0.64,
        "freshness": response["freshness"],
        "sources": response["sources"],
        "next_steps": ["Wait for the next CPI release"],
        "invalidation": ["Break below the prior earnings gap"],
    }


def test_ask_payload_caps_structured_confidence_when_sources_are_insufficient():
    class _EmptyRAGStore(_FakeRAGStore):
        def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10):
            return []

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert any(chunk.get("meta", {}).get("type") == "market_context" for chunk in context_chunks)
        return {
            "model": "test-llm",
            "answer": json.dumps(
                {
                    "action": "buy",
                    "confidence": 0.91,
                    "reasoning": [
                        "Le signal brut est fort",
                        "Mais le contexte disponible reste partiel",
                    ],
                }
            ),
            "citations": [],
        }

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Que faire sur AAPL ?",
            tickers=["AAPL"],
            max_sources=2,
            rag_store_cls=_EmptyRAGStore,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FakeContextService,
        )
    )

    assert response["quality_status"] == "insufficient_sources"
    assert response["requirements_met"]["min_sources_2"] is False
    assert response["sources_count"] == 1
    assert response["confidence"] == 0.45
    assert "Sources insuffisantes" in response["risk_caveat"]
    assert response["memo"]["verdict"] == "buy"
    assert response["memo"]["horizon"] == "1w"
    assert response["memo"]["why"] == response["why"]
    assert any("Sources insuffisantes" in item for item in response["memo"]["risks"])
    assert response["memo"]["confidence"] == 0.45
    assert response["memo"]["freshness"] == response["freshness"]
    assert response["memo"]["sources"] == response["sources"]


def test_ask_payload_uses_saved_portfolio_context_when_request_has_no_tickers(monkeypatch):
    captured_scope: Dict[str, Any] = {}

    class _EmptyRAGStore(_FakeRAGStore):
        def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10):
            captured_scope["scope"] = dict(scope or {})
            return []

    monkeypatch.setattr(
        copilot_service,
        "_resolve_saved_portfolio_context",
        lambda _scope=None: {
            "portfolio": {
                "id": "portfolio-123",
                "name": "Core",
                "tickers": ["AAPL", "MSFT"],
                "tickers_count": 2,
                "state": {
                    "horizon": "1y",
                    "conviction": "high",
                    "risk_tolerance": "moderate",
                },
            },
            "risk_profile": "balanced",
            "risk_level": "medium",
            "why": [
                "Weights remain close to the saved allocation target.",
            ],
            "warnings": [],
            "source": ["portfolio_service", "copilot_saved_portfolio"],
        },
    )

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert "Portefeuille: Core" in question
        assert "Tickers suivis: AAPL, MSFT" in question
        assert "Horizon: 1y" in question
        assert "Conviction: high" in question
        assert "Tolerance au risque: moderate" in question
        assert "Profil de risque: balanced" in question
        assert "Niveau de risque: medium" in question
        return {
            "model": "test-llm",
            "answer": json.dumps(
                {
                    "action": "buy",
                    "reasoning": ["Le portefeuille reste solide."],
                }
            ),
            "citations": [],
        }

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="What should I do with my portfolio today?",
            max_sources=2,
            rag_store_cls=_EmptyRAGStore,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FakeContextService,
        )
    )

    assert captured_scope["scope"]["tickers"] == ["AAPL", "MSFT"]
    assert response["action"] == "buy"
    assert response["portfolio_context"]["portfolio"]["id"] == "portfolio-123"
    assert response["portfolio_context"]["portfolio"]["state"] == {
        "horizon": "1y",
        "conviction": "high",
        "risk_tolerance": "moderate",
    }
    assert response["context_influence"] == {
        "mode": "portfolio_aware",
        "portfolio_applied": True,
        "source": "saved_portfolio_default",
        "requested_tickers": [],
        "effective_tickers": ["AAPL", "MSFT"],
        "portfolio_id": "portfolio-123",
        "portfolio_state": {
            "horizon": "1y",
            "conviction": "high",
            "risk_tolerance": "moderate",
        },
    }


def test_ask_payload_keeps_explicit_tickers_without_saved_portfolio_default(monkeypatch):
    captured_scope: Dict[str, Any] = {}

    class _EmptyRAGStore(_FakeRAGStore):
        def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10):
            captured_scope["scope"] = dict(scope or {})
            return []

    def fail_saved_portfolio_resolution(_scope=None):
        raise AssertionError("saved portfolio default should not run for explicit ticker asks")

    monkeypatch.setattr(
        copilot_service,
        "_resolve_saved_portfolio_context",
        fail_saved_portfolio_resolution,
    )

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert "Portefeuille:" not in question
        return {"model": "test-llm", "answer": "HOLD NVDA pour le moment.", "citations": []}

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Que faire sur NVDA aujourd'hui ?",
            tickers=["NVDA"],
            max_sources=2,
            rag_store_cls=_EmptyRAGStore,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FakeContextService,
        )
    )

    assert captured_scope["scope"]["tickers"] == ["NVDA"]
    assert response["action"] == "hold"
    assert "portfolio_context" not in response
    assert response["context_influence"] == {
        "mode": "market_wide",
        "portfolio_applied": False,
        "source": "explicit_tickers",
        "requested_tickers": ["NVDA"],
        "effective_tickers": ["NVDA"],
    }


def test_ask_payload_defaults_to_judge_stack_llm(monkeypatch):
    class _EmptyRAGStore(_FakeRAGStore):
        def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10):
            return []

    judge_calls: List[Dict[str, Any]] = []

    class _JudgeModule:
        @staticmethod
        def call_llm(*, messages, mode=None, timeout=None, category_preference=None, **_kwargs):
            judge_calls.append(
                {
                    "messages": messages,
                    "mode": mode,
                    "timeout": timeout,
                    "category_preference": category_preference,
                }
            )
            return {
                "ok": True,
                "model": "judge-stack-test",
                "answer": json.dumps(
                    {
                        "action": "buy",
                        "confidence": 0.62,
                        "reasoning": [
                            "Le brief du jour reste constructif",
                            "Le contexte marché conserve un biais favorable",
                        ],
                    }
                ),
            }

    class _RagModule:
        RAGStore = _EmptyRAGStore

    def fake_import_module(path: str):
        if path == "research.rag_store":
            return _RagModule
        if path == "domains.judge.application.g4f_client":
            return _JudgeModule
        if path == "research.llm_client":
            raise AssertionError("legacy ask_llm fallback should not be used")
        raise ImportError(path)

    monkeypatch.setattr(copilot_service, "import_module", fake_import_module)

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Que faire sur NVDA aujourd'hui ?",
            tickers=["NVDA"],
            max_sources=2,
            context_service_cls=_FakeContextService,
        )
    )

    assert judge_calls
    assert judge_calls[0]["category_preference"] == "forecast"
    assert judge_calls[0]["messages"][0]["role"] == "system"
    assert "Que faire sur NVDA aujourd'hui ?" in judge_calls[0]["messages"][1]["content"]
    assert response["model"] == "judge-stack-test"
    assert response["action"] == "buy"
    assert response["verdict"] == "buy"


def test_build_context_payload_includes_daily_brief_and_entry_points(monkeypatch):
    brief_snapshot = {
        "data": {
            "daily": {
                "summary": "Ouverture calme sur les mega caps avec un biais favorable aux semi-conducteurs.",
                "market_sentiment": "BULLISH",
                "macro_signals": [
                    {"name": "CPI", "value": "2.1%", "signal": "stable"},
                ],
                "sector_rotation": {
                    "top": ["Semiconductors"],
                    "bottom": ["Utilities"],
                },
                "generated_at": "2026-03-02T08:30:00Z",
                "source": ["test_brief"],
            }
        }
    }

    monkeypatch.setattr(
        storage_io,
        "load_json",
        lambda key: brief_snapshot if key == "brief_daily" else None,
    )

    response = asyncio.run(
        copilot_service.build_context_payload(
            context_service_cls=_FakeContextService,
            scope={"tickers": ["nvda"]},
        )
    )

    brief = response.get("daily_brief") or {}
    assert brief.get("summary", "").startswith("Ouverture calme")
    assert brief.get("market_sentiment") == "BULLISH"
    assert brief.get("source") == ["test_brief"]
    assert response.get("scope_tickers") == ["NVDA"]

    entry_points = response.get("entry_points") or []
    assert [item.get("id") for item in entry_points] == ["brief_of_day", "ask_copilot", "open_copilot"]
    assert entry_points[0].get("target") == "/brief/daily"
    assert entry_points[1].get("target") == "/copilot/ask"
    assert entry_points[1].get("prefill", {}).get("tickers") == ["NVDA"]
    assert entry_points[1].get("prefill", {}).get("question") == (
        "Que dois-je surveiller aujourd'hui sur NVDA ?"
    )
    assert entry_points[2].get("target") == "/copilot"
    copilot_start = response.get("copilot_start") or {}
    assert copilot_start.get("brief_of_day", {}).get("summary", "").startswith("Ouverture calme")
    assert [item.get("id") for item in copilot_start.get("ask", [])] == [
        "portfolio_today",
        "market_theme",
        "nvda_memo",
    ]
    assert [item.get("id") for item in copilot_start.get("open", [])] == [
        "market",
        "opportunities",
        "copilot",
    ]
    assert copilot_start.get("open", [])[0].get("target") == "market"
    assert copilot_start.get("ask", [])[0].get("prefill", {}).get("tickers") == ["NVDA"]


def test_build_context_payload_uses_saved_portfolio_scope_when_tickers_are_missing(monkeypatch):
    monkeypatch.setattr(storage_io, "load_json", lambda _key: None)
    monkeypatch.setattr(
        copilot_service,
        "_resolve_saved_portfolio_context",
        lambda _scope=None: {
            "portfolio": {
                "id": "portfolio-123",
                "name": "Core",
                "tickers": ["AAPL", "MSFT"],
                "tickers_count": 2,
                "state": {
                    "horizon": "1y",
                    "conviction": "high",
                    "risk_tolerance": "moderate",
                },
            },
            "risk_profile": "balanced",
            "risk_level": "medium",
            "weights": {
                "AAPL": 0.72,
                "MSFT": 0.28,
            },
            "why": ["Saved weights stay close to target."],
            "warnings": [],
            "source": ["portfolio_service", "copilot_saved_portfolio"],
        },
    )

    response = asyncio.run(
        copilot_service.build_context_payload(
            context_service_cls=_FakeContextService,
        )
    )

    assert response.get("scope_tickers") == ["AAPL", "MSFT"]
    assert response.get("portfolio_context", {}).get("portfolio", {}).get("id") == "portfolio-123"
    assert response.get("portfolio_context", {}).get("portfolio", {}).get("state") == {
        "horizon": "1y",
        "conviction": "high",
        "risk_tolerance": "moderate",
    }
    assert response.get("entry_points", [])[1].get("prefill", {}).get("tickers") == [
        "AAPL",
        "MSFT",
    ]
    assert response.get("copilot_start", {}).get("ask", [])[0].get("prefill", {}).get("tickers") == [
        "AAPL",
        "MSFT",
    ]
    assert response.get("context_influence") == {
        "mode": "portfolio_aware",
        "portfolio_applied": True,
        "source": "saved_portfolio_default",
        "requested_tickers": [],
        "effective_tickers": ["AAPL", "MSFT"],
        "portfolio_id": "portfolio-123",
        "portfolio_state": {
            "horizon": "1y",
            "conviction": "high",
            "risk_tolerance": "moderate",
        },
    }
    assert response.get("regime_detection") == {
        "label": "BULL_MARKET",
        "confidence": 0.73,
        "confidence_pct": 73.0,
        "threshold_reason": "vix bas",
        "source": ["forecasts", "macro", "news"],
        "generated_at": "2026-03-02T21:00:00Z",
    }

    drift_alerts = response.get("allocation_drift_alerts") or {}
    assert drift_alerts.get("active") is True
    assert drift_alerts.get("weights_analyzed") == {"AAPL": 72.0, "MSFT": 28.0}
    assert [item.get("id") for item in drift_alerts.get("alerts", [])] == [
        "largest_position_concentration",
        "equal_weight_rebalance_watch",
    ]
    assert drift_alerts.get("alerts", [])[0].get("threshold_pct") == 20.0
    assert drift_alerts.get("alerts", [])[1].get("threshold_pct") == 5.0


def test_build_context_payload_fallback_keeps_daily_brief_contract(monkeypatch):
    class _FailingContextService:
        async def get_current_market_context(self) -> Dict[str, Any]:
            raise RuntimeError("context unavailable")

    monkeypatch.setattr(storage_io, "load_json", lambda _key: None)

    response = asyncio.run(
        copilot_service.build_context_payload(
            context_service_cls=_FailingContextService,
        )
    )

    brief = response.get("daily_brief") or {}
    assert brief.get("summary") == "No daily brief available yet."
    assert brief.get("market_sentiment") == "UNKNOWN"
    assert brief.get("source") == ["brief_daily_fallback"]

    entry_points = response.get("entry_points") or []
    assert [item.get("id") for item in entry_points] == ["brief_of_day", "ask_copilot", "open_copilot"]
    assert entry_points[1].get("prefill", {}).get("question", "").startswith(
        "Que dois-je surveiller aujourd'hui"
    )
    copilot_start = response.get("copilot_start") or {}
    assert copilot_start.get("brief_of_day", {}).get("summary") == "No daily brief available yet."
    assert [item.get("id") for item in copilot_start.get("ask", [])] == [
        "portfolio_today",
        "market_theme",
        "nvda_memo",
    ]
    assert [item.get("id") for item in copilot_start.get("open", [])] == [
        "market",
        "opportunities",
        "copilot",
    ]
    assert copilot_start.get("open", [])[0].get("target") == "market"


def test_ask_payload_includes_local_daily_brief_when_brief_route_is_unavailable(monkeypatch):
    class _EmptyRAGStore(_FakeRAGStore):
        def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10):
            return []

    brief_snapshot = {
        "data": {
            "daily": {
                "summary": "Les semi-conducteurs restent leaders avant l'ouverture.",
                "market_sentiment": "BULLISH",
                "macro_signals": [
                    {"name": "Rates", "value": "stable", "signal": "neutral"},
                ],
                "sector_rotation": {
                    "top": ["Semiconductors"],
                    "bottom": ["Utilities"],
                },
            }
        }
    }

    monkeypatch.setattr(
        storage_io,
        "load_json",
        lambda key: brief_snapshot if key == "brief_daily" else None,
    )

    def _raise_backend_unavailable(*args, **kwargs):
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_backend_unavailable)

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert "Les semi-conducteurs restent leaders avant l'ouverture." in question
        assert "Sentiment: BULLISH" in question
        return {"model": "test-llm", "answer": "Je recommande HOLD sur NVDA.", "citations": []}

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Que faire sur NVDA aujourd'hui ?",
            tickers=["NVDA"],
            max_sources=2,
            rag_store_cls=_EmptyRAGStore,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FakeContextService,
        )
    )

    assert response.get("action") == "hold"
    assert response.get("sources_count") == 1
