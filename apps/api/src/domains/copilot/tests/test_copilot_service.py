"""Copilot ask payload tests."""

import asyncio
import json
import urllib.request
from typing import Any, Dict, List, Optional

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
    assert [item.get("id") for item in entry_points] == ["brief_of_day", "ask_copilot"]
    assert entry_points[0].get("target") == "/brief/daily"
    assert entry_points[1].get("target") == "/copilot/ask"
    assert entry_points[1].get("prefill", {}).get("tickers") == ["NVDA"]


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
    assert brief.get("source") == ["copilot_daily_brief_fallback"]

    entry_points = response.get("entry_points") or []
    assert [item.get("id") for item in entry_points] == ["brief_of_day", "ask_copilot"]


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
