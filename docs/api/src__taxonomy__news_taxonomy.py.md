# news_taxonomy.py

news_taxonomy.py
-----------------
Common taxonomies + lightweight taggers used by the news pipeline.

Design goals
- **Pure-Python, zero external deps** (regex + simple rules)
- Fast, language-agnostic best-effort (works on EN/FR/DE text)
- Safe to call on every article (title/summary/body)

Provides
- SECTOR_KEYWORDS: industry lexicons (banking, energy, defense, etc.)
- EVENT_PATTERNS: regexes to detect events (M&A, earnings, guidance, sanctions...)
- GEO_KEYWORDS: geopolitics taxonomy (Ukraine, Gaza, BRICS, NATO, tariffs, etc.)
- COMMODITY_KEYWORDS: crude, gas, gold, copper, wheat, etc.
- RISK_KEYWORDS: strikes, cyberattack, recall, antitrust, export ban...

- tag_sectors(text)
- classify_event(text)
- tag_geopolitics(text)
- tag_commodities(text)
- tag_risks(text)

Return format: sorted unique lowercase tags (list[str]).

## Function: `tag_sectors`

Signature: `def tag_sectors(...)->List[str]`

Inputs:
- `text`: str
Returns: `List[str]`

## Function: `classify_event`

Signature: `def classify_event(...)->List[str]`

Inputs:
- `text`: str
Returns: `List[str]`

## Function: `tag_geopolitics`

Signature: `def tag_geopolitics(...)->List[str]`

Inputs:
- `text`: str
Returns: `List[str]`

## Function: `tag_commodities`

Signature: `def tag_commodities(...)->List[str]`

Inputs:
- `text`: str
Returns: `List[str]`

## Function: `tag_risks`

Signature: `def tag_risks(...)->List[str]`

Inputs:
- `text`: str
Returns: `List[str]`
