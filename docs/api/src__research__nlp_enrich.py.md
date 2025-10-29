# nlp_enrich.py

Lightweight NLP enrichment utilities with zero external dependencies.

Features:
- Multi-level summarization: headline (<= 120 chars), bullets (3-6 pts), narrative (short paragraph)
- Rule-based sentiment (domain-aware, finance + geopolitics lexicons)
- Simple entity extraction: companies (heuristics), tickers (regex), ISIN/CUSIP, countries/commodities
- Language hints: cheap heuristics + pluggable translator callback
- Clean dataclass API + pure functions; safe to run per-article

Intended usage:
from nlp_enrich import enrich_article
item = enrich_article(title, summary, body, source="ft", region="INTL")

Optional translator: pass translator=str->str callable (e.g., wrapper to DeepL/OpenAI/etc.)

No external imports beyond stdlib.

## Function: `summarize`

Signature: `def summarize(...)->str | List[str]`

Very small extractive summarizer.
level: 'headline' | 'bullets' | 'narrative'
- headline: best short sentence/fragment <= 120 chars
- bullets: 3..max_bullets bullet points (key sentences)
- narrative: 3-5 sentences stitched

Inputs:
- `text`: str
- `level`: str = 'headline'
- `max_bullets`: int = 5
Returns: `str | List[str]`

## Function: `sentiment_score`

Signature: `def sentiment_score(...)->float`

Return sentiment in [-5, 5] (closer to finance-style magnitude).
Zero means neutral. Sign captures polarity; magnitude scales with density.

Inputs:
- `text`: str
Returns: `float`

## Function: `extract_entities`

Signature: `def extract_entities(...)->Dict[str, List[str]]`

Inputs:
- `title`: str
- `summary`: str = ''
- `body`: str = ''
Returns: `Dict[str, List[str]]`

## Function: `guess_language`

Signature: `def guess_language(...)->str`

Inputs:
- `text`: str
Returns: `str`

## Class: `EnrichedArticle`

### Method: `EnrichedArticle.asdict`

Signature: `def asdict(...)->Dict`

Inputs:
- (none)
Returns: `Dict`

## Function: `enrich_article`

Signature: `def enrich_article(...)->EnrichedArticle`

Compose all enrichments in one call.

translator: optional callable(text, src_lang, target_lang) -> translated_text

Inputs:
- `title`: str
- `summary`: str = ''
- `body`: str = ''
- `translator`: Optional[Callable[[str, str, str], str]] = None
- `target_lang`: str = 'en'
Returns: `EnrichedArticle`

## Function: `ask_model`

Signature: `def ask_model(...)->str`

Fonction wrapper pour intégrer NLP_enrich avec l'app hub.

Prend question et contexte, retourne une réponse textuelle.

Inputs:
- `question`: str
- `context`: dict = None
Returns: `str`
