# peers_finder.py

Peers finder basé Finnhub (+ validation yfinance) — général US/CA.

Entrée: ticker Yahoo OU nom de société (ex: "NGD.TO" ou "New Gold" ou "HUT" ou "Hut 8")
Sortie: liste de tickers Yahoo US/CA plausibles (scores simples + filtres secteur/industrie/keywords)

Dépendances: yfinance, requests, numpy
Secrets: FINNHUB_API_KEY (via secrets_local.py ou variable d'env)

Exemples:
  python peers_finder.py NGD.TO --min 5 --max 10 --log DEBUG
  python peers_finder.py "Hut 8" --min 5 --max 10 --log INFO

## Function: `get_peers_auto`

Signature: `def get_peers_auto(...)->List[str]`

Inputs:
- `user_input`: str
- `min_peers`: int = 5
- `max_peers`: int = 15
- `logger_`: Any = None
Returns: `List[str]`

## Function: `find_peers`

Signature: `def find_peers(...)->Any`

Fonction d'interface avec fallback corrélation Yahoo si pas d'API Finnhub

Inputs:
- `ticker`: str
- `k`: int = 10
Returns: `Any`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
