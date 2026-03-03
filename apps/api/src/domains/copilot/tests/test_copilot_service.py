"""Copilot ask payload tests."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from domains.copilot.application import copilot_service


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
    assert response.get("sources_count") == 1
    assert response["quality_status"] == "insufficient_sources"
    assert response["requirements_met"]["min_sources_2"] is False
