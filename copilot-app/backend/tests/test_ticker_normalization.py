from __future__ import annotations

from src.core.ticker_normalization import (
    is_canonical_ticker,
    normalize_ticker,
    normalize_tickers,
)


def test_normalize_ticker_handles_share_class_and_exchange_variants():
    assert normalize_ticker("BRK-B") == "BRK.B"
    assert normalize_ticker("brk/b") == "BRK.B"
    assert normalize_ticker("BRK B") == "BRK.B"
    assert normalize_ticker("NYSE:BRK.B") == "BRK.B"
    assert normalize_ticker("BRK.B.US") == "BRK.B"


def test_normalize_ticker_handles_simple_symbols():
    assert normalize_ticker("$aapl") == "AAPL"
    assert normalize_ticker("nasdaq:aapl") == "AAPL"
    assert normalize_ticker("AAPL.US") == "AAPL"
    assert normalize_ticker("AAPL:US") == "AAPL"


def test_normalize_ticker_rejects_invalid_values():
    assert normalize_ticker("") == ""
    assert normalize_ticker("INVALID!!") == ""
    assert normalize_ticker("1234567") == ""
    assert normalize_ticker(None) == ""


def test_normalize_tickers_deduplicates_and_keeps_order():
    out = normalize_tickers(["brk-b", "BRK.B", "AAPL", "nasdaq:aapl", "", "MSFT"])
    assert out == ["BRK.B", "AAPL", "MSFT"]
    assert is_canonical_ticker("BRK.B")
    assert not is_canonical_ticker("BRK-B")
