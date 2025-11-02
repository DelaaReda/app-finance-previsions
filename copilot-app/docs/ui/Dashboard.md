# Dashboard (React)

Dernière mise à jour : 2025-11-02

## Objectif UX

Overview du jour/semaine avec TopSignals/TopRisks, mini-macro, activity feed pour une prise de décision rapide.

## Données nécessaires

- Endpoints:
  - GET /api/brief?period=weekly&universe=...
  - GET /api/macro/snapshot
  - GET /api/news/feed?limit=10
- Types TS: `webapp/src/types/brief.types.ts`, `macro.types.ts`, `news.types.ts`
- Fenêtre temporelle / pagination / perfs: weekly pour brief, snapshot pour macro, 10 news récentes

## Intégration React

- Services: `webapp/src/services/brief.service.ts`, `macro.service.ts`, `news.service.ts`
- Hooks: `webapp/src/hooks/useDashboardData.ts`
- Composants: `webapp/src/components/signals/TopSignals.tsx`, `TopRisks.tsx`, `news/RecentNews.tsx`, `macro/MiniMacro.tsx`, `common/WatchlistBar.tsx`

## États & erreurs

- Loading: skeletons pour chaque section
- Error: message "Erreur de chargement" avec bouton retry
- Empty: si pas de données, afficher "Aucune donnée disponible"
- Partial: afficher ce qui est chargé, avec indicateur pour les sections manquantes

## Tests

- Gherkin:

```
Feature: Dashboard
  Scenario: Affichage du dashboard hebdomadaire
    Given une watchlist "AAPL,NVDA,MSFT"
    When j’ouvre la page Dashboard
    Then je vois 3 cartes dans "Top Signals" et 3 dans "Top Risks"
    And je vois les badges macro avec zscores
    And je vois 10 news récentes avec source/timestamp
    And chaque section a des liens cliquables vers les pages détaillées
```

- Unit front/back + e2e smoke: vérifier chargement parallèle, cache SWR

## Exemples

- Requête brief:
```bash
curl -s "http://localhost:8050/api/brief?period=weekly&universe=AAPL,NVDA,MSFT"
```

- Réponse (tronquée):

```json
{
  "period": "weekly",
  "top_signals": [
    {"ticker": "NVDA", "score": 85, "notes": ["macro:+", "tech:+"]}
  ],
  "top_risks": [
    {"ticker": "TSLA", "score": 25}
  ],
  "asof_date": "2025-10-31",
  "hash": "..."
}
```
