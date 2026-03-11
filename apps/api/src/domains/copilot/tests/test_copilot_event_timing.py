from __future__ import annotations

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
    def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10):
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


def test_ask_payload_adds_event_timing_risk_note_from_judge_stack(monkeypatch):
    async def fake_event_timing_payload(limit: int = 3):
        assert limit == 3
        return {
            "matrix": [
                {
                    "event_type": "earnings",
                    "dominant_horizon": "1w",
                    "interpretation": "earnings has its strongest signal on the 1w horizon.",
                    "horizons": {
                        "1w": {"impact_score": 0.74},
                    },
                }
            ],
            "freshness": "2026-03-11T09:00:00Z",
            "source": ["judge_event_impact_horizon_matrix_service"],
        }

    monkeypatch.setattr(copilot_service, "_load_event_timing_payload", fake_event_timing_payload)

    def fake_ask_llm(*, question: str, context_chunks: List[Dict[str, Any]], max_tokens: int = 1000):
        assert len(context_chunks) == 2
        return {
            "model": "test-llm",
            "answer": json.dumps(
                {
                    "action": "hold",
                    "reasoning": [
                        "Momentum is still constructive",
                        "Event risk argues for smaller sizing",
                    ],
                }
            ),
            "citations": [],
        }

    response = asyncio.run(
        copilot_service.build_ask_payload(
            question="Should I add to NVDA before earnings?",
            tickers=["NVDA"],
            max_sources=2,
            rag_store_cls=_FakeRAGStore,
            ask_llm_fn=fake_ask_llm,
            context_service_cls=_FakeContextService,
        )
    )

    assert "Timing risk elevated around earnings (1w)." in response["risk_caveat"]
    assert response["event_timing"] == {
        "summary": "Timing risk elevated around earnings (1w).",
        "events": [
            {
                "event_type": "earnings",
                "dominant_horizon": "1w",
                "impact_score": 0.74,
                "interpretation": "earnings has its strongest signal on the 1w horizon.",
            }
        ],
        "freshness": "2026-03-11T09:00:00Z",
        "source": ["copilot_event_timing", "judge_event_impact_horizon_matrix_service"],
        "sources": ["copilot_event_timing", "judge_event_impact_horizon_matrix_service"],
    }
    assert response["memo"]["risks"][-1] == response["risk_caveat"]
