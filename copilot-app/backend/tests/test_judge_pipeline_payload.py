"""
Tests de contrat pour JudgePayload (taille de news autorisée).
"""
from __future__ import annotations

from src.services.judge_pipeline import JudgePayload


def test_judge_payload_accepts_twenty_news_items():
    news = [
        {
            "title": f"Article {i}",
            "summary": "Summary",
            "source": "unit-test",
            "ts": "2026-02-01T00:00:00Z",
            "tickers": ["SPY"],
        }
        for i in range(20)
    ]
    payload = JudgePayload(
        ticker="SPY",
        features={},
        phases={},
        news=news,
        attachments=[],
        meta={"source": "test"},
    )
    assert len(payload.news) == 20
