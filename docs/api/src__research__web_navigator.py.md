# web_navigator.py

## Class: `RedirectError`

## Class: `NonJSONError`

## Class: `ForbiddenError`

## Class: `TooManyRequestsError`

## Function: `fetch_searxng_instances`

Signature: `def fetch_searxng_instances(...)->list[str]`

Inputs:
- `logger_`: Any = None
Returns: `list[str]`

## Function: `search_searxng`

Signature: `def search_searxng(...)->dict`

Inputs:
- `query`: str
- `num`: int = 10
- `engines`: Iterable[str] = SEARXNG_DEFAULT_ENGINES
- `logger_`: Any = logger
Returns: `dict`

## Function: `finance_search`

Signature: `def finance_search(...)->dict`

Cherche des articles liés à un ticker, une société ou un sujet économique.
Priorise “news”, booste domaines finance, filtre bruit, période ~1 semaine si supportée.

Inputs:
- `symbol`: str | None = None
- `company`: str | None = None
- `topic`: str | None = None
- `num`: int = 12
- `logger_`: Any = logger
Returns: `dict`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
