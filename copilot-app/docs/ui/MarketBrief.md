# MarketBrief (React)

Dernière mise à jour : 2025-11-02

## Objectif UX

Scoring 40/40/20 macro/tech/news + Top Picks/Risks pour watchlist/univers avec justifications.

## Données nécessaires

- Endpoints:
  - GET /api/brief?period=daily|weekly&universe=...
- Types TS: `webapp/src/types/brief.types.ts`
- Fenêtre temporelle / pagination / perfs: daily/weekly, SWR 5 min

## Intégration React

- Services: `webapp/src/services/brief.service.ts`
- Hooks: `webapp/src/hooks/useBrief.ts`
- Composants: `webapp/src/components/brief/PicksGrid.tsx`, `RisksGrid.tsx`, `RationaleList.tsx`, `BriefHeader.tsx`

## États & erreurs

- Loading: skeletons pour grids
- Error: retry
- Empty: "Aucun brief disponible"
- Partial: afficher rationale même si picks manquent

## Tests

- Gherkin:

```
Feature: MarketBrief
  Scenario: Affichage du brief hebdomadaire
    Given une watchlist "AAPL,NVDA,MSFT"
    When j’ouvre la page MarketBrief en period "weekly"
    Then je vois 3 cartes dans "Top Signals" et 3 dans "Top Risks"
    And chaque carte affiche un score, un ticker, et une justification concise
    And les sources sont disponibles dans le détail
```

- Unit front/back + e2e smoke

## Exemples

- Requête:
```bash
curl -s "http://localhost:8050/api/brief?period=weekly&universe=AAPL,NVDA,MSFT"
```

- Réponse (tronquée):

```json
{
  "period": "weekly",
  "top_signals": [
    {"ticker": "NVDA", "score": 85, "notes": ["macro:+", "tech:+", "news:+"]}
  ],
  "top_risks": [
    {"ticker": "TSLA", "score": 25, "notes": ["tech:-", "news:-"]}
  ],
  "picks": [
    {"ticker": "AAPL", "score": 78, "notes": ["macro:+", "tech:+"]}
  ],
  "rationale": [
    "Macro : Inflation stabilisée, USD faible.",
    "Tech : Momentum positif sur IA.",
    "News : Annonces positives sur semi-conducteurs."
  ],
  "asof_date": "2025-10-31",
  "hash": "..."
}
```
