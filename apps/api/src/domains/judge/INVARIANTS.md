# Invariants - Judge Domain

- Judge never returns empty/placeholder verdict in nominal path.
- LLM selection always includes ranked providers and fallback chain.
- Response schema is source-of-truth aligned with `packages/contracts/judge_v1.py`.
- Cache keys include model/provider metadata for audit traces.
