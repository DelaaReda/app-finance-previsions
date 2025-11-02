"""Silver v2 transformation.

Reads bronze partitions, applies enrichment (readability, NER, sentiment,
topics...) and writes parquet compatible with the v2 schema.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import timedelta
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import pandas as pd

try:  # Optional but recommended for HTML cleaning
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None  # type: ignore

try:
    from langdetect import detect as lang_detect
except Exception:  # pragma: no cover - fallback naive
    def lang_detect(text: str) -> str:
        return "en"

try:
    from taxonomy.news_taxonomy import classify_event, tag_geopolitics, tag_sectors
except Exception:  # pragma: no cover - fallback stubs
    def classify_event(_text: str) -> List[str]:  # type: ignore
        return []

    def tag_geopolitics(_text: str) -> List[str]:  # type: ignore
        return []

    def tag_sectors(_text: str) -> List[str]:  # type: ignore
        return []

try:
    from core.stock_utils import guess_ticker
except Exception:  # pragma: no cover
    def guess_ticker(_name: str) -> str | None:
        return None

try:
    from research.nlp_enrich import EnrichedArticle, enrich_article
except Exception:  # pragma: no cover
    EnrichedArticle = None  # type: ignore

    def enrich_article(*_args, **_kwargs):  # type: ignore
        raise RuntimeError("nlp_enrich module not available")


BRONZE_DIR = Path("data/news/bronze")
SILVER_DIR = Path("data/news/silver_v2")

TIER1_DOMAINS = {
    "reuters.com",
    "wsj.com",
    "bloomberg.com",
    "ft.com",
    "cnbc.com",
    "marketwatch.com",
    "nytimes.com",
    "economist.com",
    "washingtonpost.com",
}
TIER3_DOMAINS = {
    "seekingalpha.com",
    "reddit.com",
    "medium.com",
    "substack.com",
}
TIER_WEIGHTS = {"Tier1": 1.0, "Tier2": 0.7, "Tier3": 0.4}


def _iter_bronze_partitions(pattern: str) -> Iterator[Path]:
    for path in sorted(BRONZE_DIR.glob(f"dt={pattern}/**/*.parquet")):
        yield path


def _load_partition(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  Failed to read {path}: {exc}")
        return pd.DataFrame()


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _ensure_timestamp(value: object) -> Optional[pd.Timestamp]:
    if value is None or value == "":
        return None
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    return ts if ts is not None and not pd.isna(ts) else None


def _extract_text(raw_html: Optional[str], summary: str, title: str) -> str:
    if raw_html and BeautifulSoup:
        try:
            soup = BeautifulSoup(raw_html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = " ".join(fragment.strip() for fragment in soup.stripped_strings)
            if text:
                return text[:8000]
        except Exception:
            pass
    basis = ". ".join(filter(None, [summary, title]))
    return basis[:4000]


def _source_tier(domain: Optional[str]) -> str:
    if not domain:
        return "Tier2"
    host = domain.lower()
    if host in TIER1_DOMAINS:
        return "Tier1"
    if host in TIER3_DOMAINS:
        return "Tier3"
    return "Tier2"


def _simhash(text: str, bits: int = 64) -> str:
    if not text:
        return "0" * (bits // 4)
    vector = [0] * bits
    for token in text.split():
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        for i in range(bits):
            bitmask = 1 << i
            vector[i] += 1 if h & bitmask else -1
    fingerprint = 0
    for i, weight in enumerate(vector):
        if weight > 0:
            fingerprint |= 1 << i
    return f"{fingerprint:016x}"


def _build_entities(enriched: Optional[EnrichedArticle]) -> List[Dict[str, object]]:
    if not enriched:
        return []
    entities: List[Dict[str, object]] = []
    for etype, values in enriched.entities.items():
        if not isinstance(values, list):
            continue
        for value in values:
            entities.append({"type": etype, "value": value, "score": 1.0})
    return entities


def _quality_metrics(text: str, tier_weight: float) -> Dict[str, float]:
    length = len(text)
    completeness = _clamp(length / 1500.0)
    noise = _clamp(1.0 - min(length, 2500) / 2500.0)
    credibility = _clamp(0.5 + 0.5 * tier_weight)
    return {
        "credibility": round(credibility, 3),
        "completeness": round(completeness, 3),
        "noise": round(noise, 3),
    }


def _impact_proxy(tier_weight: float, sentiment: float, ticker_count: int, has_geo: bool) -> float:
    base = 0.2 + 0.4 * tier_weight
    sentiment_component = 0.3 * abs(sentiment)
    ticker_component = 0.1 * min(ticker_count / 3.0, 1.0)
    geo_component = 0.1 if has_geo else 0.0
    return round(_clamp(base + sentiment_component + ticker_component + geo_component), 3)


def _market_window_ref(published: pd.Timestamp) -> Dict[str, pd.Timestamp]:
    return {
        "t0": published,
        "t1d": published + pd.Timedelta(days=1),
        "t5d": published + pd.Timedelta(days=5),
        "t20d": published + pd.Timedelta(days=20),
    }


def _safe_enrich(title: str, summary: str, text: str) -> Optional[EnrichedArticle]:
    if not callable(enrich_article):  # type: ignore[arg-type]
        return None
    try:
        return enrich_article(title=title, summary=summary, body=text)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  enrich_article failed: {exc}")
        return None


def _process_row(row: Dict[str, object]) -> Optional[Dict[str, object]]:
    published = _ensure_timestamp(row.get("published_at"))
    if published is None:
        return None
    crawled = _ensure_timestamp(row.get("crawled_at")) or published

    title = (row.get("title") or "").strip()
    summary = (row.get("summary") or "").strip()
    raw_html = row.get("raw_html") if isinstance(row.get("raw_html"), str) else None
    text = _extract_text(raw_html, summary, title)

    enriched = _safe_enrich(title, summary, text)

    lang = None
    if enriched and enriched.language != "unknown":
        lang = enriched.language
    elif row.get("lang_detected"):
        lang = str(row.get("lang_detected"))
    else:
        lang = lang_detect(" ".join(filter(None, [title, summary, text])))

    sentiment = 0.0
    if enriched:
        sentiment = _clamp((enriched.sentiment or 0.0) / 5.0, -1.0, 1.0)

    entities = _build_entities(enriched)
    tickers: List[str] = []
    if enriched:
        tickers.extend(enriched.entities.get("tickers", []))
        for company in enriched.entities.get("companies", []) or []:
            guess = guess_ticker(company) if company else None
            if guess:
                tickers.append(guess)

    # also consider any tickers already provided upstream
    upstream_tickers = row.get("tickers")
    if isinstance(upstream_tickers, list):
        tickers.extend(str(t) for t in upstream_tickers)

    tickers = sorted({t.upper() for t in tickers if t})

    domain = row.get("source_domain")
    tier = _source_tier(str(domain) if domain is not None else None)
    tier_weight = TIER_WEIGHTS.get(tier, 0.7)

    sectors = tag_sectors(text) if callable(tag_sectors) else []
    events = classify_event(text) if callable(classify_event) else []
    geopolitics = tag_geopolitics(text) if callable(tag_geopolitics) else []
    topics = sorted({*sectors, *events})

    quality = _quality_metrics(text, tier_weight)
    impact = _impact_proxy(tier_weight, sentiment, len(tickers), bool(geopolitics))

    summary_out = summary or (enriched.headline if enriched else "")
    entities_struct = entities

    hash_text = hashlib.sha1((text + str(published) + str(domain)).encode("utf-8")).hexdigest()
    simhash = _simhash(text)

    market_windows = _market_window_ref(published)

    return {
        "id": row.get("id"),
        "canonical_url": row.get("canonical_url") or row.get("url") or "",
        "source_domain": domain,
        "source_name": row.get("source_name"),
        "source_tier": tier,
        "region": row.get("region"),
        "lang": lang,
        "published_at": published,
        "crawled_at": crawled,
        "title": title,
        "summary": summary_out,
        "text": text,
        "authors": row.get("authors") if isinstance(row.get("authors"), list) else [],
        "tickers": tickers,
        "topics": topics,
        "entities": entities_struct,
        "geopolitics": geopolitics,
        "sentiment": {"polarity": sentiment, "subjectivity": _clamp(abs(sentiment) * 1.2)},
        "quality": quality,
        "relevance": round(_clamp(abs(sentiment) * 0.6 + 0.2 * len(topics)), 3),
        "impact_proxy": impact,
        "market_window_ref": market_windows,
        "hash_text": hash_text,
        "dedup_key": hash_text,
        "simhash": simhash,
        "parent_id": None,
        "schema_version": 2,
    }


def _apply_enrichment(df: pd.DataFrame) -> pd.DataFrame:
    records: Dict[str, Dict[str, object]] = {}
    for row in df.to_dict("records"):
        processed = _process_row(row)
        if not processed:
            continue
        key = processed["hash_text"]
        current = records.get(key)
        if current is None or processed["impact_proxy"] > current["impact_proxy"]:
            records[key] = processed
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(list(records.values()))


def _persist(df: pd.DataFrame, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    output = target_dir / "silver.parquet"
    df.to_parquet(output, index=False)
    with (target_dir / "metadata.json").open("w", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "row_count": len(df),
                    "columns": sorted(df.columns.tolist()),
                },
                indent=2,
            )
        )
    print(f"✅ wrote {output}")


def to_silver_v2(dt_glob: str = "*") -> None:
    partitions = list(_iter_bronze_partitions(dt_glob))
    if not partitions:
        print("ℹ️  no bronze partitions matched pattern")
        return

    frames: List[pd.DataFrame] = []
    for path in partitions:
        df = _load_partition(path)
        if not df.empty:
            frames.append(df)
    if not frames:
        print("⚠️  bronze partitions had no rows")
        return

    bronze = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["id"])
    bronze["published_at"] = pd.to_datetime(bronze["published_at"], utc=True, errors="coerce")
    bronze["crawled_at"] = pd.to_datetime(bronze.get("crawled_at"), utc=True, errors="coerce")

    silver = _apply_enrichment(bronze)
    if silver.empty:
        print("⚠️  no enriched rows produced")
        return

    silver["published_at"] = pd.to_datetime(silver["published_at"], utc=True)

    for dt_value, group in silver.groupby(silver["published_at"].dt.strftime("%Y-%m-%d")):
        target = SILVER_DIR / f"dt={dt_value}"
        _persist(group, target)


if __name__ == "__main__":
    to_silver_v2()
