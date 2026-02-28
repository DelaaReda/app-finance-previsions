"""
Ticker normalization contract (US equities first).

Canonical format:
  - Uppercase symbol
  - Optional share class as `.X` or `.XY` (example: BRK.B)
  - No exchange prefixes/suffixes
"""

from __future__ import annotations

import re
from typing import Iterable, List


CANONICAL_TICKER_RE = re.compile(r"^[A-Z0-9]{1,6}(?:\.[A-Z0-9]{1,2})?$")

_EXCHANGE_PREFIX_RE = re.compile(
    r"^(?:NYSE|NASDAQ|NASDAQGS|NASDAQGM|AMEX|ARCA|BATS|OTC|US)[:/.-](.+)$",
    flags=re.IGNORECASE,
)
_TRAILING_MARKET_SUFFIXES = {
    "US",
    "N",
    "O",
    "NY",
    "NQ",
    "OQ",
}


def is_canonical_ticker(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    return bool(CANONICAL_TICKER_RE.fullmatch(value.strip().upper()))


def normalize_ticker(value: str | None) -> str:
    """
    Normalize ticker variants to canonical representation.

    Examples:
      - BRK-B, BRK/B, brk b -> BRK.B
      - NYSE:BRK.B, BRK.B.US -> BRK.B
      - nasdaq:aapl, $aapl -> AAPL
    """
    if value is None:
        return ""

    s = str(value).strip().upper()
    if not s:
        return ""

    if s.startswith("$"):
        s = s[1:]

    # Remove known exchange prefix(es), if present.
    for _ in range(2):
        m = _EXCHANGE_PREFIX_RE.match(s)
        if not m:
            break
        s = (m.group(1) or "").strip().upper()

    # Handle symbol:US / symbol/US style.
    if s.endswith(":US") or s.endswith("/US"):
        s = s[:-3]

    # Convert common class separators to dot (BRK-B, BRK/B, BRK B -> BRK.B).
    class_sep = re.fullmatch(r"([A-Z0-9]{1,6})[-/ ]([A-Z0-9]{1,2})", s)
    if class_sep:
        s = f"{class_sep.group(1)}.{class_sep.group(2)}"

    # Strip trailing market suffix (AAPL.US, BRK.B.US, AAPL.NQ).
    parts = s.split(".")
    if len(parts) >= 2 and parts[-1] in _TRAILING_MARKET_SUFFIXES:
        s = ".".join(parts[:-1])

    # Remove accidental duplicate separators.
    s = re.sub(r"\.+", ".", s).strip(".")

    if not is_canonical_ticker(s):
        return ""
    return s


def normalize_tickers(values: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        ticker = normalize_ticker(value)
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        out.append(ticker)
    return out

