# Stocks (React)

Dernière mise à jour : 2025-11-02

## Objectif UX

Analyse technique actionable par ticker avec indicateurs clés.

## Données nécessaires

- Endpoints:
  - GET /api/stocks/indicators?ticker=...
- Types TS: `webapp/src/types/stocks.types.ts`
- Fenêtre temporelle / pagination / perfs: LTTB appliqué backend, 200+ points min

## Intégration React

- Services: `webapp/src/services/stocks.service.ts`
- Hooks: `webapp/src/hooks/useStockData.ts`
- Composants: `webapp/src/components/charts/PriceChart.tsx`, `stocks/IndicatorTable.tsx`, `common/TickerPicker.tsx`

## États & erreurs

- Loading: skeleton chart et table
- Error: retry button
- Empty: "Sélectionnez un ticker"
- Partial: afficher prix même si indicateurs partiels

## Tests

- Gherkin:

```
Feature: Stocks Indicators
  Scenario: Chart indicateurs
    Given je sélectionne "NVDA"
    When la page charge les indicateurs
    Then le chart prix s’affiche avec SMA et RSI
    And l’axe du temps est aligné entre toutes les séries
    And il y a au moins 200 points
```

- Unit front/back + e2e smoke

## Exemples

- Requête:
```bash
curl -s "http://localhost:8050/api/stocks/indicators?ticker=NVDA"
```

- Réponse (tronquée):

```json
{
  "ticker": "NVDA",
  "price": [
    {"t": "2025-10-01", "v": 150.0},
    {"t": "2025-10-02", "v": 152.5}
  ],
  "sma": [
    {"t": "2025-10-01", "v": 149.5}
  ],
  "rsi": [
    {"t": "2025-10-01", "v": 65.0}
  ],
  "asof_date": "2025-10-31",
  "source": "yfinance/indicators",
  "hash": "..."
}
```
