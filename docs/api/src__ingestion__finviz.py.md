# finviz.py

Finviz provider (HTML parsing, no auth)
Couvre:
- Global news:        https://finviz.com/news.ashx?v=2
- Company news:       https://finviz.com/quote.ashx?t=<TICKER>
- Insider (global):   https://finviz.com/insidertrading.ashx (et variantes)
- Insider (company):  https://finviz.com/quote.ashx?t=<TICKER> (bloc News/Insider)
- Analyst ratings:    https://finviz.com/quote.ashx?t=<TICKER> (bloc Upgrades/Downgrades)
- Snapshot métriques: https://finviz.com/quote.ashx?t=<TICKER> (tableau “snapshot”)
- Détention instits:  https://finviz.com/quote.ashx?t=<TICKER> (table holders, si présent)

Sorties : listes de dict “bruts” compatibles avec la couche de normalisation finnews
 (title, link, published ISO Z, summary, raw_text, source, _id) + champs spécifiques “kind”.

## Class: `FinvizClient`

### Method: `FinvizClient.get`

Signature: `def get(...)->requests.Response`

Inputs:
- `url`: str
- `params`: Optional[Dict] = None
Returns: `requests.Response`

### Method: `FinvizClient.fetch_global_news`

Signature: `def fetch_global_news(...)->List[Dict]`

Parse https://finviz.com/news.ashx?v=2
Retourne : [{title, link, published, summary, raw_text, source, _id, kind='news'}]

Inputs:
- `limit`: int = 200
Returns: `List[Dict]`

### Method: `FinvizClient.fetch_company_news`

Signature: `def fetch_company_news(...)->List[Dict]`

Parse https://finviz.com/quote.ashx?t=<TICKER> (bloc News)

Inputs:
- `ticker`: str
- `limit`: int = 120
Returns: `List[Dict]`

### Method: `FinvizClient.fetch_insider_recent`

Signature: `def fetch_insider_recent(...)->List[Dict]`

Parse des tables globales d'insiders.
Pages typiques: https://finviz.com/insidertrading.ashx (ou avec params)
Retour: [{kind='insider', action, owner, relationship, ticker, date, shares, price, value, link, source, _id}]

Inputs:
- `limit`: int = 200
Returns: `List[Dict]`

### Method: `FinvizClient.fetch_company_insiders`

Signature: `def fetch_company_insiders(...)->List[Dict]`

Gratte la page quote et tente d'extraire un tableau 'Insider' pour ce ticker (quand présent).

Inputs:
- `ticker`: str
- `limit`: int = 80
Returns: `List[Dict]`

### Method: `FinvizClient.fetch_company_ratings`

Signature: `def fetch_company_ratings(...)->List[Dict]`

Repère un bloc 'Upgrades/Downgrades' ou colonnes avec 'Analyst', 'Rating', 'Price Target' sur la page quote.
Retour: [{kind='rating', ticker, analyst, action, rating_from, rating_to, pt_from, pt_to, published, source, link, _id}]

Inputs:
- `ticker`: str
- `limit`: int = 60
Returns: `List[Dict]`

### Method: `FinvizClient.fetch_company_snapshot`

Signature: `def fetch_company_snapshot(...)->Dict`

Récupère le tableau “snapshot” (pairs label: value) sur la quote.
Retour: dict {kind='snapshot', ticker, metrics:{...}, source, link, _id, published}

Inputs:
- `ticker`: str
Returns: `Dict`

### Method: `FinvizClient.fetch_company_institutions`

Signature: `def fetch_company_institutions(...)->List[Dict]`

Tente de trouver un tableau “Holders / Institutional” dans la page quote.
Retour: [{kind='institution', ticker, holder, position, pct, change, date, source, link, _id, published}]

Inputs:
- `ticker`: str
- `limit`: int = 120
Returns: `List[Dict]`

## Function: `fetch_finviz_global_news`

Signature: `def fetch_finviz_global_news(...)->List[Dict]`

Inputs:
- `limit`: int = 200
- `timeout`: int = 20
- `sleep_between`: float = 0.6
Returns: `List[Dict]`

## Function: `fetch_finviz_company_news`

Signature: `def fetch_finviz_company_news(...)->List[Dict]`

Inputs:
- `ticker`: str
- `limit`: int = 120
- `timeout`: int = 20
- `sleep_between`: float = 0.6
Returns: `List[Dict]`

## Function: `fetch_finviz_insider_recent`

Signature: `def fetch_finviz_insider_recent(...)->List[Dict]`

Inputs:
- `limit`: int = 200
- `timeout`: int = 20
- `sleep_between`: float = 0.6
Returns: `List[Dict]`

## Function: `fetch_finviz_company_insiders`

Signature: `def fetch_finviz_company_insiders(...)->List[Dict]`

Inputs:
- `ticker`: str
- `limit`: int = 80
- `timeout`: int = 20
- `sleep_between`: float = 0.6
Returns: `List[Dict]`

## Function: `fetch_finviz_company_ratings`

Signature: `def fetch_finviz_company_ratings(...)->List[Dict]`

Inputs:
- `ticker`: str
- `limit`: int = 60
- `timeout`: int = 20
- `sleep_between`: float = 0.6
Returns: `List[Dict]`

## Function: `fetch_finviz_company_snapshot`

Signature: `def fetch_finviz_company_snapshot(...)->Dict`

Inputs:
- `ticker`: str
- `timeout`: int = 20
- `sleep_between`: float = 0.6
Returns: `Dict`

## Function: `fetch_finviz_company_institutions`

Signature: `def fetch_finviz_company_institutions(...)->List[Dict]`

Inputs:
- `ticker`: str
- `limit`: int = 120
- `timeout`: int = 20
- `sleep_between`: float = 0.6
Returns: `List[Dict]`
