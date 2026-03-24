# Free Data Source Key Matrix

Updated: 2026-03-02
Scope: forecast and analysis only.

## Usage classes

- `NO_KEY`: utilisable sans clé API.
- `KEY_REQUIRED`: clé obligatoire pour l'API officielle.
- `KEY_OPTIONAL`: utilisable sans clé en fallback, mais clé recommandée pour stabilité/quota.

## Source registry (prêt à implémenter)

## `SRC-FRED`
- Layer: macro US
- Class: `KEY_REQUIRED` (API JSON officielle)
- Env var: `FRED_API_KEY`
- Fallback gratuit: endpoint CSV public FRED
- Cadence conseillée: 1h
- Implémentation actuelle: `apps/api/src/platform/legacy/jobs/macro_ingest.py`, `apps/api/src/platform/legacy/core/market_data.py`

## `SRC-WORLDBANK`
- Layer: macro country/world
- Class: `NO_KEY`
- Env var: none
- Fallback gratuit: none needed (API publique)
- Cadence conseillée: 6h à 24h

## `SRC-ECB`
- Layer: macro EU/rates
- Class: `NO_KEY`
- Env var: none
- Fallback gratuit: none needed
- Cadence conseillée: 1h à 6h

## `SRC-EUROSTAT`
- Layer: macro EU stats
- Class: `NO_KEY`
- Env var: none
- Fallback gratuit: none needed
- Cadence conseillée: 24h

## `SRC-OECD`
- Layer: macro international
- Class: `NO_KEY` (quota/rate à surveiller)
- Env var: none
- Fallback gratuit: WorldBank/IMF selon indicateur
- Cadence conseillée: 6h à 24h

## `SRC-IMF`
- Layer: macro international
- Class: `NO_KEY` (selon endpoint SDMX)
- Env var: none
- Fallback gratuit: OECD/WorldBank
- Cadence conseillée: 24h

## `SRC-EIA`
- Layer: énergie/commodities
- Class: `KEY_REQUIRED`
- Env var: `EIA_API_KEY`
- Fallback gratuit: séries publiques alternatives (ex: FRED commodities)
- Cadence conseillée: 1h à 6h

## `SRC-SEC-EDGAR`
- Layer: insiders/filings/ownership
- Class: `NO_KEY`
- Env var: `SEC_USER_AGENT` (obligatoire côté bonnes pratiques)
- Fallback gratuit: none needed
- Cadence conseillée: 1h à 6h
- Implémentation actuelle: `apps/api/src/platform/legacy/ingestion/financials_ownership_client.py`

## `SRC-GDELT`
- Layer: géopolitique/news events
- Class: `NO_KEY`
- Env var: none
- Fallback gratuit: RSS + classification locale
- Cadence conseillée: 15min à 1h

## `SRC-UCDP`
- Layer: conflit armé (historique/structuré)
- Class: `NO_KEY` (API publique)
- Env var: none
- Fallback gratuit: GDELT/ACLED selon granularité
- Cadence conseillée: 24h

## `SRC-ACLED`
- Layer: conflit armé (granulaire)
- Class: `KEY_REQUIRED`
- Env var: `ACLED_API_KEY`, `ACLED_EMAIL`
- Fallback gratuit: UCDP + GDELT
- Cadence conseillée: 24h

## `SRC-REGULATIONS-GOV`
- Layer: régulation US
- Class: `KEY_REQUIRED` (api.data.gov)
- Env var: `DATA_GOV_API_KEY`
- Fallback gratuit: scraping/feeds publics ciblés (à limiter)
- Cadence conseillée: 6h à 24h

## `SRC-CONGRESS-GOV`
- Layer: législation US
- Class: `KEY_REQUIRED`
- Env var: `CONGRESS_API_KEY`
- Fallback gratuit: GovInfo + flux publics
- Cadence conseillée: 6h à 24h

## `SRC-GOVINFO`
- Layer: documents légaux/réglementaires US
- Class: `KEY_REQUIRED` (clé API)
- Env var: `GOVINFO_API_KEY`
- Fallback gratuit: Congress.gov, Regulations.gov
- Cadence conseillée: 6h à 24h

## `SRC-EU-PUBLICATIONS-SPARQL`
- Layer: régulation UE
- Class: `NO_KEY`
- Env var: none
- Fallback gratuit: EUR-Lex APIs/exports selon besoin
- Cadence conseillée: 24h

## `SRC-STOOQ`
- Layer: market prices fallback
- Class: `NO_KEY`
- Env var: none
- Fallback gratuit: Yahoo chart API path
- Cadence conseillée: 15min à 1h
- Implémentation actuelle: `apps/api/src/platform/legacy/jobs/stocks_prices_refresh.py`

## `SRC-YAHOO-CHART`
- Layer: market prices fallback
- Class: `NO_KEY`
- Env var: none
- Fallback gratuit: Stooq
- Cadence conseillée: 15min à 1h
- Implémentation actuelle: `apps/api/src/platform/legacy/jobs/stocks_prices_refresh.py`

## `SRC-YAHOO-RSS`
- Layer: financial news
- Class: `NO_KEY`
- Env var: none
- Fallback gratuit: Google News RSS
- Cadence conseillée: 10min à 30min
- Implémentation actuelle: `apps/api/src/platform/legacy/jobs/news_ingest.py`

## `SRC-GOOGLE-NEWS-RSS`
- Layer: topical news by ticker/theme
- Class: `NO_KEY`
- Env var: none
- Fallback gratuit: Yahoo RSS / market sources
- Cadence conseillée: 10min à 30min
- Implémentation actuelle: `apps/api/src/platform/legacy/jobs/news_ingest.py`

## Bootstrap recommendation for dev speed

## Phase 1 (zéro clé)
- Activer d'abord: `SEC-EDGAR`, `WorldBank`, `ECB`, `Eurostat`, `GDELT`, `Stooq`, `Yahoo RSS`, `Google News RSS`.
- Objectif: pipeline multi-couches fonctionnel sans onboarding API keys.

## Phase 2 (clés à forte valeur)
- Ajouter: `FRED_API_KEY`, `EIA_API_KEY`, `DATA_GOV_API_KEY`, `CONGRESS_API_KEY`, `GOVINFO_API_KEY`, `ACLED_API_KEY`.
- Objectif: meilleure qualité macro/énergie/réglementaire/conflit.

## Runtime guardrails

- Si source `KEY_REQUIRED` indisponible:
- ne jamais casser le contrat API;
- basculer en degraded mode explicite;
- réduire confiance de couche concernée;
- tracer `source_unavailable` dans provenance.

- Si fallback utilisé plus de N cycles:
- remonter un blocker qualité dans le gate batch en cours.
