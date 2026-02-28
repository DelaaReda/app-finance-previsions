# Invariants - Market Data Domain

- All external data ingestion goes through market_data application services.
- Route handlers are thin adapters over services.
- Public responses expose normalized error envelopes and explicit freshness metadata.
- Snapshot jobs and APIs share the same storage adapter interfaces.
