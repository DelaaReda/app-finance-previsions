"""Event extraction v1.

Extract structured events (earnings, guidance, M&A, regulatory, product) from
silver v2 articles using lightweight heuristics. Designed to be swapped for a
more advanced hybrid rules/LLM extractor later.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import pandas as pd

SILVER_DIR = Path("data/news/silver_v2")
EVENTS_DIR = Path("data/news/gold/events_v1")

KEYWORDS: Dict[str, List[str]] = {
    "earnings": ["earnings", "eps", "quarter", "guidance", "topline"],
    "guidance": ["guidance", "forecast", "outlook"],
    "mna": ["acquire", "merger", "buyout", "stake", "takeover"],
    "regulatory": ["sec", "antitrust", "investigation", "fine", "lawsuit"],
    "product": ["launch", "product", "chip", "service", "platform"],
}

QUALIFIERS = {
    "beat": ["beat", "beats", "topped", "above expectations"],
    "miss": ["miss", "missed", "below expectations"],
    "raise": ["raise", "raised", "hike", "increase", "boost"],
    "cut": ["cut", "lower", "reduced", "trim"],
    "investigation": ["investigation", "probe", "inquiry"],
    "penalty": ["fine", "penalty", "sanction"],
}

VALUE_PATTERNS = {
    "eps": re.compile(r"(?:EPS|earnings per share)\s*(?:of|at|was|were|is|stood at)?\s*[$€£]?(-?\d+(?:\.\d+)?)", re.I),
    "revenue": re.compile(r"revenue[s]?\s*(?:of|at|were|total(?:ed)?|came in at)?\s*[$€£]?(-?\d+(?:\.\d+)?)\s*(billion|million|thousand|bn|mn|m|k)?", re.I),
    "guidance_eps": re.compile(r"guidance\s*(?:for|on)?\s*(?:EPS|earnings)\s*(?:of|at)?\s*[$€£]?(-?\d+(?:\.\d+)?)", re.I),
    "guidance_revenue": re.compile(r"guidance\s*(?:for|on)?\s*revenue\s*(?:of|at)?\s*[$€£]?(-?\d+(?:\.\d+)?)\s*(billion|million|thousand|bn|mn|m|k)?", re.I),
    "deal_value": re.compile(r"deal\s*(?:valued|worth)\s*(?:at)?\s*[$€£]?(-?\d+(?:\.\d+)?)\s*(billion|million|thousand|bn|mn|m|k)?", re.I),
}

UNIT_MULTIPLIERS = {
    None: 1.0,
    "billion": 1e9,
    "bn": 1e9,
    "million": 1e6,
    "mn": 1e6,
    "m": 1e6,
    "thousand": 1e3,
    "k": 1e3,
}


def _iter_silver(pattern: str) -> Iterator[Path]:
    yield from sorted(SILVER_DIR.glob(f"dt={pattern}/silver.parquet"))


def _load(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  failed to read {path}: {exc}")
        return pd.DataFrame()


def _classify(text: str, topics: List[str]) -> Optional[str]:
    lowered = text.lower()
    topic_set = {t.lower() for t in topics}
    if "earnings" in topic_set:
        return "earnings"
    if "guidance" in topic_set:
        return "guidance"
    if "mna" in topic_set or "m&a" in topic_set:
        return "mna"
    if "regulation" in topic_set or "regulatory" in topic_set:
        return "regulatory"
    if "product" in topic_set:
        return "product"
    for event_type, keywords in KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return event_type
    return None


def _event_id(event_type: str, tickers: List[str], date_str: str, source: str) -> str:
    base = f"{event_type}|{','.join(sorted(tickers))}|{date_str}|{source}"
    return hashlib.sha1(base.encode()).hexdigest()


def _detect_qualifiers(text: str) -> List[str]:
    lowered = text.lower()
    found: List[str] = []
    for qualifier, phrases in QUALIFIERS.items():
        if any(p in lowered for p in phrases):
            found.append(qualifier)
    return sorted(set(found))


def _parse_numeric(match: re.Match) -> Optional[float]:
    try:
        value = float(match.group(1))
    except Exception:
        return None
    unit = match.group(2).lower() if match.lastindex and match.group(match.lastindex) else None
    multiplier = UNIT_MULTIPLIERS.get(unit, 1.0)
    return value * multiplier


def _extract_values(event_type: str, text: str) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    if event_type in {"earnings", "guidance"}:
        for key in ("eps", "guidance_eps"):
            pattern = VALUE_PATTERNS.get(key)
            if not pattern:
                continue
            match = pattern.search(text)
            if match:
                value = _parse_numeric(match)
                results.append({"name": "eps", "value": value, "unit": "currency_per_share"})
                break
        for key in ("revenue", "guidance_revenue"):
            pattern = VALUE_PATTERNS.get(key)
            if not pattern:
                continue
            match = pattern.search(text)
            if match:
                value = _parse_numeric(match)
                unit = match.group(2).lower() if match.lastindex and match.group(match.lastindex) else None
                results.append({"name": "revenue", "value": value, "unit": unit or "currency"})
                break
    if event_type == "mna":
        pattern = VALUE_PATTERNS["deal_value"]
        match = pattern.search(text)
        if match:
            value = _parse_numeric(match)
            unit = match.group(2).lower() if match.lastindex and match.group(match.lastindex) else None
            results.append({"name": "deal_value", "value": value, "unit": unit or "currency"})
    return results


def _confidence(event_type: str, values: List[Dict[str, object]], qualifiers: List[str], tickers: List[str]) -> float:
    base = 0.45
    if values:
        base += 0.25
    if qualifiers:
        base += 0.1
    if len(tickers) > 1:
        base += 0.05
    if event_type in {"earnings", "guidance"} and any(v.get("name") == "eps" for v in values):
        base += 0.05
    return round(min(base, 0.95), 2)


def _normalize_list(raw) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        iterable = raw
    else:
        try:
            iterable = list(raw)
        except TypeError:
            iterable = [raw]
    return [str(t) for t in iterable if t]


def _extract_tickers(raw) -> List[str]:
    return sorted({item.upper() for item in _normalize_list(raw) if item})


def extract_events_v1(dt_glob: str = "*") -> None:
    partitions = list(_iter_silver(dt_glob))
    if not partitions:
        print("ℹ️  no silver partitions for events")
        return

    for path in partitions:
        df = _load(path)
        if df.empty:
            continue

        rows: List[Dict] = []
        for _, row in df.iterrows():
            tickers = _extract_tickers(row.get("tickers"))
            if not tickers:
                continue
            text = " ".join(filter(None, [row.get("title", ""), row.get("summary", ""), row.get("text", "")]))
            topics = _normalize_list(row.get("topics"))
            event_type = _classify(text, topics)
            if not event_type:
                continue
            published = pd.to_datetime(row.get("published_at"), utc=True)
            event_date = published.date() if not pd.isna(published) else None
            if event_date is None:
                continue
            qualifiers = _detect_qualifiers(text)
            values = _extract_values(event_type, text)
            confidence = _confidence(event_type, values, qualifiers, tickers)
            rows.append(
                {
                    "event_id": _event_id(event_type, tickers, str(event_date), row.get("source_domain", "")),
                    "event_type": event_type,
                    "tickers": tickers,
                    "company_name": row.get("source_name"),
                    "event_date": event_date,
                    "values": values,
                    "qualifiers": qualifiers,
                    "source_id": row.get("id"),
                    "confidence": confidence,
                    "extracted_at": pd.Timestamp.utcnow(),
                    "schema_version": 1,
                    "needs_review": confidence < 0.7,
                }
            )

        if not rows:
            continue

        date_component = Path(path).parent.name.split("=")[1]
        target_dir = EVENTS_DIR / f"dt={date_component}"
        target_dir.mkdir(parents=True, exist_ok=True)
        out = target_dir / "events.parquet"
        pd.DataFrame(rows).to_parquet(out, index=False)
        print(f"✅ wrote {out}")


if __name__ == "__main__":
    extract_events_v1()
