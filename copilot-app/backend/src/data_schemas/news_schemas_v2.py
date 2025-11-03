"""PyArrow schemas for the news lakehouse v2.

These schemas extend the current ingestion models with long‑term fields
required for ML/RAG workloads (events, embeddings, graph, labels).
"""
from __future__ import annotations

import pyarrow as pa

# Bronze layer (raw immutable ingest)
bronze_schema = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("url", pa.string()),
        pa.field("canonical_url", pa.string()),
        pa.field("source_domain", pa.string()),
        pa.field("source_name", pa.string()),
        pa.field("lang_detected", pa.string()),
        pa.field("region", pa.string()),
        pa.field("paywall", pa.bool_()),
        pa.field("published_at", pa.timestamp("ns", tz="UTC")),
        pa.field("crawled_at", pa.timestamp("ns", tz="UTC")),
        pa.field("raw_html", pa.string()),
        pa.field("license_hint", pa.string()),
        pa.field("schema_version", pa.int32()),
    ]
)

# Silver layer (clean + enriched)
silver_schema = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("canonical_url", pa.string()),
        pa.field("source_domain", pa.string()),
        pa.field("source_name", pa.string()),
        pa.field("source_tier", pa.string()),
        pa.field("lang", pa.string()),
        pa.field("published_at", pa.timestamp("ns", tz="UTC")),
        pa.field("crawled_at", pa.timestamp("ns", tz="UTC")),
        pa.field("title", pa.string()),
        pa.field("summary", pa.string()),
        pa.field("text", pa.string()),
        pa.field("authors", pa.list_(pa.string())),
        pa.field(
            "entities",
            pa.list_(
                pa.struct(
                    [
                        pa.field("type", pa.string()),
                        pa.field("value", pa.string()),
                        pa.field("score", pa.float32()),
                    ]
                )
            ),
        ),
        pa.field("topics", pa.list_(pa.string())),
        pa.field("tickers", pa.list_(pa.string())),
        pa.field(
            "sentiment",
            pa.struct(
                [
                    pa.field("polarity", pa.float32()),
                    pa.field("subjectivity", pa.float32()),
                ]
            ),
        ),
        pa.field(
            "quality",
            pa.struct(
                [
                    pa.field("credibility", pa.float32()),
                    pa.field("completeness", pa.float32()),
                    pa.field("noise", pa.float32()),
                ]
            ),
        ),
        pa.field("relevance", pa.float32()),
        pa.field("dedup_key", pa.string()),
        pa.field("simhash", pa.string()),
        pa.field("parent_id", pa.string()),
        pa.field(
            "market_window_ref",
            pa.struct(
                [
                    pa.field("t0", pa.timestamp("ns", tz="UTC")),
                    pa.field("t1d", pa.timestamp("ns", tz="UTC")),
                    pa.field("t5d", pa.timestamp("ns", tz="UTC")),
                    pa.field("t20d", pa.timestamp("ns", tz="UTC")),
                ]
            ),
        ),
        pa.field("impact_proxy", pa.float32()),
        pa.field("schema_version", pa.int32()),
    ]
)

# Gold features (daily ticker aggregates)
features_daily_schema = pa.schema(
    [
        pa.field("date", pa.date32()),
        pa.field("ticker", pa.string()),
        pa.field("news_count", pa.int32()),
        pa.field("novelty", pa.float32()),
        pa.field("sent_mean", pa.float32()),
        pa.field("sent_pos_share", pa.float32()),
        pa.field("sent_neg_share", pa.float32()),
        pa.field("tier1_share", pa.float32()),
        pa.field("top_topics", pa.list_(pa.string())),
        pa.field("intraday_intensity", pa.float32()),
        pa.field("impact_proxy_mean", pa.float32()),
        pa.field("source_impact_factor", pa.float32()),
        pa.field("features_version", pa.int32()),
    ]
)

# Events table (structured news events)
events_schema = pa.schema(
    [
        pa.field("event_id", pa.string()),
        pa.field("event_type", pa.string()),
        pa.field("tickers", pa.list_(pa.string())),
        pa.field("company_name", pa.string()),
        pa.field("event_date", pa.date32()),
        pa.field(
            "values",
            pa.list_(
                pa.struct(
                    [
                        pa.field("name", pa.string()),
                        pa.field("value", pa.float64()),
                        pa.field("unit", pa.string()),
                    ]
                )
            ),
        ),
        pa.field("qualifiers", pa.list_(pa.string())),
        pa.field("source_id", pa.string()),
        pa.field("confidence", pa.float32()),
        pa.field("extracted_at", pa.timestamp("ns", tz="UTC")),
        pa.field("schema_version", pa.int32()),
        pa.field("needs_review", pa.bool_()),
    ]
)

# Embeddings layer
embeddings_schema = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("news_id", pa.string()),
        pa.field("chunk_idx", pa.int32()),
        pa.field("text_chunk", pa.string()),
        pa.field("embedding", pa.list_(pa.float32())),
        pa.field("lang", pa.string()),
        pa.field("tickers", pa.list_(pa.string())),
        pa.field("published_at", pa.timestamp("ns", tz="UTC")),
        pa.field("embedding_version", pa.int32()),
        pa.field("chunk_policy", pa.string()),
    ]
)

# Knowledge graph nodes and edges
kg_nodes_schema = pa.schema(
    [
        pa.field("node_id", pa.string()),
        pa.field("type", pa.string()),
        pa.field("name", pa.string()),
        pa.field("aliases", pa.list_(pa.string())),
        pa.field("ticker", pa.string()),
        pa.field("country", pa.string()),
        pa.field("sector", pa.string()),
        pa.field("created_at", pa.timestamp("ns", tz="UTC")),
        pa.field("updated_at", pa.timestamp("ns", tz="UTC")),
    ]
)

kg_edges_schema = pa.schema(
    [
        pa.field("edge_id", pa.string()),
        pa.field("src_node_id", pa.string()),
        pa.field("dst_node_id", pa.string()),
        pa.field("rel_type", pa.string()),
        pa.field("weight", pa.float32()),
        pa.field("first_seen", pa.timestamp("ns", tz="UTC")),
        pa.field("last_seen", pa.timestamp("ns", tz="UTC")),
        pa.field("source_ids", pa.list_(pa.string())),
    ]
)

# Label tables for ML
labels_returns_schema = pa.schema(
    [
        pa.field("date", pa.date32()),
        pa.field("ticker", pa.string()),
        pa.field("fwd_ret_1d", pa.float32()),
        pa.field("fwd_ret_5d", pa.float32()),
        pa.field("fwd_ret_20d", pa.float32()),
        pa.field("fwd_vol_20d", pa.float32()),
        pa.field("realized_drawdown_20d", pa.float32()),
        pa.field("label_version", pa.int32()),
    ]
)

labels_events_schema = pa.schema(
    [
        pa.field("event_id", pa.string()),
        pa.field("ticker", pa.string()),
        pa.field("car_window", pa.string()),
        pa.field("abnormal_return", pa.float32()),
        pa.field("vol_spike", pa.float32()),
        pa.field("drift", pa.float32()),
        pa.field("label_version", pa.int32()),
    ]
)

__all__ = [
    "bronze_schema",
    "silver_schema",
    "features_daily_schema",
    "events_schema",
    "embeddings_schema",
    "kg_nodes_schema",
    "kg_edges_schema",
    "labels_returns_schema",
    "labels_events_schema",
]
