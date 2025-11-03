# News (React)

Dernière mise à jour : 2025-11-02

## Objectif UX

Explorer le flux d’actualités et les features agrégées par ticker.

## Données nécessaires

- Endpoints:
  - GET /api/news/feed?ticker=...&start=...&end=...&q=...&page=...&limit=50
  - GET /api/news/features/daily?ticker=...
- Types TS: `webapp/src/types/news.types.ts`
- Fenêtre temporelle / pagination / perfs: pagination 50 items, cache <300ms

## Intégration React

- Services: `webapp/src/services/news.service.ts`
- Hooks: `webapp/src/hooks/useNews.ts`, `useNewsFeatures.ts`
- Composants: `webapp/src/components/news/NewsFeed.tsx`, `NewsCard.tsx`, `NewsFilters.tsx`, `FeaturesPanel.tsx`

## États & erreurs

- Loading: skeleton list
- Error: retry
- Empty: "Aucune news trouvée"
- Partial: afficher feed même si features manquent

## Tests

- Gherkin:

```
Feature: News Feed
  Scenario: Filtrer par mot-clé et ticker
    Given je suis sur la page News
    When je saisis "AAPL" dans Ticker et "AI" dans Keyword
    Then la liste affiche 50 articles max
    And chaque article contient un titre, une source et un lien cliquable
```

- Unit front/back + e2e smoke

## Exemples

- Requête feed:
```bash
curl -s "http://localhost:8050/api/news/feed?ticker=AAPL&q=AI&page=1&limit=50"
```

- Réponse (tronquée):

```json
[
  {
    "id": "news123",
    "ticker": "AAPL",
    "title": "Apple annonce nouveau produit IA",
    "url": "https://example.com/news123",
    "source": "Reuters",
    "published_at": "2025-10-31T09:00:00Z",
    "sentiment": 0.8
  }
]
```

- Requête features:
```bash
curl -s "http://localhost:8050/api/news/features/daily?ticker=AAPL"
```

- Réponse:

```json
[
  {
    "ticker": "AAPL",
    "date": "2025-10-31",
    "news_count": 15,
    "sent_mean": 0.6,
    "novelty": 0.4,
    "tier1_share": 0.7,
    "impact_proxy_mean": 0.5
  }
]
```
