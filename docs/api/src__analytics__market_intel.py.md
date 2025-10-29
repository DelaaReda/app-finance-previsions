# market_intel.py

Market Intelligence Orchestrator
- Agrège Nouvelles (finnews), Ownership & Insiders (financials_ownership_client),
  et optionnellement Finviz (company snapshot / options / technicals) + Macro/Futures (macro_derivatives_client).
- Produit un JSON unifié et des features agrégées compatibles avec econ_llm_agent.

Sorties:
- "news": liste normalisée d'items (JSONL-friendly)
- "features": dict de métriques (globales ou par ticker s'il est fourni)
- "meta": contexte & sources utilisées

Usage CLI:
  python -m src.analytics.market_intel run       --regions US,CA,INTL --window last_week --limit 200       --outdir data/real --prefix auto
  python -m src.analytics.market_intel run       --ticker NGD --query "gold OR mine" --regions US,INTL       --limit 150 --outdir artifacts

Auteur: toi

## Function: `now_utc`

Signature: `def now_utc(...)->dt.datetime`

Inputs:
- (none)
Returns: `dt.datetime`

## Function: `iso`

Signature: `def iso(...)->str`

Inputs:
- `dtobj`: Optional[dt.datetime] = None
Returns: `str`

## Function: `collect_news`

Signature: `def collect_news(...)->Tuple[List[Dict[str, Any]], Dict[str, Any]]`

Inputs:
- `regions`: List[str]
- `window`: str
- `query`: str = ''
- `company`: Optional[str] = None
- `aliases`: Optional[List[str]] = None
- `tgt_ticker`: Optional[str] = None
- `per_source_cap`: Optional[int] = None
- `limit`: int = 150
Returns: `Tuple[List[Dict[str, Any]], Dict[str, Any]]`

## Function: `collect_ownership`

Signature: `def collect_ownership(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
Returns: `Dict[str, Any]`

## Function: `collect_finviz`

Signature: `def collect_finviz(...)->Dict[str, Any]`

Inputs:
- `ticker`: Optional[str]
- `want_futures`: bool
Returns: `Dict[str, Any]`

## Function: `collect_macro_derivs`

Signature: `def collect_macro_derivs(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `build_unified_features`

Signature: `def build_unified_features(...)->Dict[str, Any]`

Inputs:
- `news_items`: List[Dict[str, Any]]
- `target_ticker`: Optional[str]
- `ownership`: Optional[Dict[str, Any]]
- `finviz_blob`: Optional[Dict[str, Any]]
- `macro_blob`: Optional[Dict[str, Any]]
Returns: `Dict[str, Any]`

## Function: `build_snapshot`

Signature: `def build_snapshot(...)->Dict[str, Any]`

Retourne un JSON unifié: {news:[...], features:{...}, meta:{...}, ownership?:{...}, finviz?:{...}, macro?:{...}}

Inputs:
- `regions`: List[str]
- `window`: str
- `query`: str = ''
- `ticker`: Optional[str] = None
- `company`: Optional[str] = None
- `aliases`: Optional[List[str]] = None
- `limit`: int = 150
- `per_source_cap`: Optional[int] = None
- `include_finviz`: bool = True
- `include_futures`: bool = True
- `include_macro_derivs`: bool = False
Returns: `Dict[str, Any]`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- `argv`: Optional[List[str]] = None
Returns: `Any`
