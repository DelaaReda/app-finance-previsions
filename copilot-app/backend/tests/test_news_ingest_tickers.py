"""
Tests de non-régression pour l'extraction de tickers news.
"""
from __future__ import annotations

from jobs.news_ingest import extract_tickers, DEFAULT_TICKERS


def test_extract_tickers_detects_spy_from_sp500_context():
    article = {
        "title": "S&P 500 rallies as Fed rate-cut hopes grow",
        "summary": "Broad market gains lifted major US indices.",
    }

    tickers = extract_tickers(article, known_tickers=set(DEFAULT_TICKERS))
    assert "SPY" in tickers


def test_extract_tickers_uses_source_hint_when_text_is_sparse():
    article = {
        "title": "Earnings recap",
        "summary": "Latest quarter highlights.",
    }

    tickers = extract_tickers(
        article,
        known_tickers=set(DEFAULT_TICKERS),
        source_name="Yahoo Finance - NVDA",
    )
    assert "NVDA" in tickers

