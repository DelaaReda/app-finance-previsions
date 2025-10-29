# phase4_sentiment.py

Phase 4 — Sentiment & News / NLP pour actions US/CA

Sources "sans clé":
  - yfinance.Ticker.news  (titres + liens + éditeur + datetime)
  - (Optionnel) RSS SEC / SEDAR+ si vous fournissez l'URL RSS
  - (Optionnel) Texte libre passé par l'API (ex: dépêches que vous scrapez)

Pipeline:
  fetch -> clean -> dedupe -> score_sentiment (VADER + HF si dispo) ->
  summarize (TextRank light) -> extract_events -> aggregate (daily/weekly) ->
  produce signals (news shock, drift, risk flags)

Auteur: toi + IA (2025) — Licence MIT (à adapter)

## Class: `NewsItem`

### Method: `NewsItem.key`

Signature: `def key(...)->str`

Inputs:
- (none)
Returns: `str`

## Class: `SentimentDetail`

### Method: `SentimentDetail.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `EventSignal`

Événements structurés extraits d’un article.

### Method: `EventSignal.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `ScoredNews`

### Method: `ScoredNews.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `AggregateSentiment`

Agrégations par jour/semaine.

### Method: `AggregateSentiment.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `fetch_yf_news`

Signature: `def fetch_yf_news(...)->List[NewsItem]`

Récupère des news via yfinance (titres + lien). Texte intégral non garanti.

Inputs:
- `ticker`: str
- `max_items`: int = 40
Returns: `List[NewsItem]`

## Function: `fetch_rss`

Signature: `def fetch_rss(...)->List[NewsItem]`

Parser RSS minimaliste (sans dépendances) — fonctionne pour flux ATOM/RSS simples.
Utilisez pour SEC/SEDAR si vous avez l’URL, sinon ignorez.

Inputs:
- `url`: str
- `ticker_hint`: Optional[str] = None
- `max_items`: int = 50
Returns: `List[NewsItem]`

## Function: `score_sentiment`

Signature: `def score_sentiment(...)->SentimentDetail`

Ensemble: VADER et/ou HF ; priorité au titre.

Inputs:
- `title`: str
- `abstract`: str = ''
- `weight_title`: float = 0.65
Returns: `SentimentDetail`

## Function: `summarize_textrank`

Signature: `def summarize_textrank(...)->str`

TextRank très light basé sur similarité TF (cosinus) — sans lib externe.
Pour titres courts, retourne le texte original.

Inputs:
- `sentences`: List[str]
- `k`: int = 3
Returns: `str`

## Function: `extract_events`

Signature: `def extract_events(...)->List[EventSignal]`

Inputs:
- `text`: str
- `max_events`: int = 4
Returns: `List[EventSignal]`

## Function: `dedupe_news`

Signature: `def dedupe_news(...)->List[NewsItem]`

Inputs:
- `items`: List[NewsItem]
Returns: `List[NewsItem]`

## Function: `score_news_items`

Signature: `def score_news_items(...)->List[ScoredNews]`

Inputs:
- `items`: List[NewsItem]
Returns: `List[ScoredNews]`

## Function: `aggregate_sentiment`

Signature: `def aggregate_sentiment(...)->AggregateSentiment`

Inputs:
- `scored`: List[ScoredNews]
Returns: `AggregateSentiment`

## Function: `build_sentiment_view`

Signature: `def build_sentiment_view(...)->Dict[str, Any]`

Récupère, note, agrège, et retourne un snapshot prêt pour l'UI.

Args:
  ticker: symbole
  rss_urls: liste d’URLs RSS supplémentaires (facultatif)
  extra_texts: liste de (title, text) pour intégrer vos propres sources
  max_items: limite news par source

Returns:
  dict avec: items_scored (n<50), aggregates, top_stories, signals

Inputs:
- `ticker`: str
- `rss_urls`: Optional[List[str]] = None
- `extra_texts`: Optional[List[Tuple[str, str]]] = None
- `max_items`: int = 60
Returns: `Dict[str, Any]`
