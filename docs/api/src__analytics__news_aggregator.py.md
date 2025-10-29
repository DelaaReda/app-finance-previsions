# news_aggregator.py

News aggregation and summarization helpers.

Collects normalized news via analytics.market_intel.collect_news and produces
LLM-assisted summaries when econ_llm_agent is available, with safe fallback.

## Function: `aggregate_news`

Signature: `def aggregate_news(...)->Dict[str, Any]`

Inputs:
- `regions`: List[str]
- `window`: str = 'last_week'
- `query`: str = ''
- `company`: Optional[str] = None
- `tgt_ticker`: Optional[str] = None
- `limit`: int = 200
Returns: `Dict[str, Any]`

## Function: `summarize_news`

Signature: `def summarize_news(...)->Dict[str, Any]`

LLM summary via econ_llm_agent when available, otherwise simple counts.

Returns: { "ok": bool, "text": str, "json": dict|None }

Inputs:
- `news_items`: List[Dict[str, Any]]
- `locale`: str = 'fr-FR'
Returns: `Dict[str, Any]`
