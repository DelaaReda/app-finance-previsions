# TickerSheet (React)

Dernière mise à jour : 2025-11-02

## Objectif UX

Vue 360° d’un ticker : résumé, indicateurs clés, dernières news, chart multi-pistes.

## Données nécessaires

- Endpoints:
  - GET /api/stocks/indicators?ticker=...
  - GET /api/news/features/daily?ticker=...
  - GET /api/news/feed?ticker=...&limit=5
  - Extrait de GET /api/brief pour le ticker
- Types TS: `webapp/src/types/stocks.types.ts`, `news.types.ts`, `brief.types.ts`
- Fenêtre temporelle / pagination / perfs: composition, P95 <500ms

## Intégration React

- Services: `webapp/src/services/stocks.service.ts`, `news.service.ts`, `brief.service.ts`
- Hooks: `webapp/src/hooks/useTickerSheet.ts`
- Composants: `webapp/src/components/ticker/TickerHeader.tsx`, `KeyMetrics.tsx`, `charts/MultiPaneChart.tsx`, `news/NewsStrip.tsx`

## États & erreurs

- Loading: skeletons pour chaque section
- Error: retry par section
- Empty: "Données non disponibles pour ce ticker"
- Partial: afficher ce qui est chargé

## Tests

- Gherkin:

```
Feature: TickerSheet
  Scenario: Vue détaillée d’un ticker
    Given je sélectionne "AAPL"
    When la page charge
    Then je vois 3 sections visibles
    And le chart multi-pistes s’affiche
    And les dernières news sont listées
    And la latence est <500ms
```

- Unit front/back + e2e smoke

## Exemples

- Composition d'appels API pour charger toutes les données nécessaires.
- Réponse combinée affichée dans les composants.
