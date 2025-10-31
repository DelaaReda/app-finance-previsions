"""Event extraction v1 skeleton.

Uses keyword heuristics to detect event types from silver v2 articles.
Swap the classifier with your hybrid rules/LLM system when ready.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterator, List

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


def _iter_silver(pattern: str) -> Iterator[Path]:
    yield from sorted(SILVER_DIR.glob(f"dt={pattern}/silver.parquet"))


def _load(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  failed to read {path}: {exc}")
        return pd.DataFrame()


def _classify(text: str) -> str | None:
    lowered = text.lower()
    for event_type, keywords in KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return event_type
    return None


def _event_id(event_type: str, tickers: List[str], date_str: str, source: str) -> str:
    base = f"{event_type}|{','.join(sorted(tickers))}|{date_str}|{source}"
    return hashlib.sha1(base.encode()).hexdigest()


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
            tickers = row.get("tickers") or []
            if not tickers:
                continue
            text = f"{row.get('title', '')} {row.get('text', '')}"
            event_type = _classify(text)
            if not event_type:
                continue
            published = pd.to_datetime(row.get("published_at"), utc=True)
            event_date = published.date() if not pd.isna(published) else None
            rows.append(
                {
                    "event_id": _event_id(event_type, tickers, str(event_date), row.get("source_domain", "")),
                    "event_type": event_type,
                    "tickers": tickers,
                    "company_name": row.get("source_name"),
                    "event_date": event_date,
                    "values": [],
                    "qualifiers": [],
                    "source_id": row.get("id"),
                    "confidence": 0.5,
                    "extracted_at": pd.Timestamp.utcnow(),
                    "schema_version": 1,
                    "needs_review": True,
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
