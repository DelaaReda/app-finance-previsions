"""
Tests de non-régression pour l'extraction de tickers news.
"""
from __future__ import annotations

from jobs.news_ingest import (
    extract_tickers,
    DEFAULT_TICKERS,
    parse_published_datetime,
    build_dynamic_sources,
)


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


def test_parse_published_datetime_supports_rfc822():
    dt = parse_published_datetime("Wed, 04 Feb 2026 23:57:15 +0000")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 2
    assert dt.day == 4


def test_build_dynamic_sources_adds_two_sources_per_ticker():
    sources = build_dynamic_sources(["AAPL", "SPY"])
    names = {s["name"] for s in sources}
    assert "Yahoo Finance - AAPL" in names
    assert "Google News - AAPL" in names
    assert "Yahoo Finance - SPY" in names
    assert "Google News - SPY" in names
