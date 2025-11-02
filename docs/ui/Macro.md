# Macro (React)

Dernière mise à jour : 2025-11-02

## Objectif UX

Rendre lisible le régime macro (GRW/INF/POL/USD/CMD) et ses drivers pour comprendre le contexte économique.

## Données nécessaires

- Endpoints:
  - GET /api/macro/snapshot
- Types TS: `webapp/src/types/macro.types.ts`
- Fenêtre temporelle / pagination / perfs: snapshot actuel, cache 30-60 min

## Intégration React

- Services: `webapp/src/services/macro.service.ts`
- Hooks: `webapp/src/hooks/useMacroData.ts`
- Composants: `webapp/src/components/charts/MacroChart.tsx`, `macro/MacroBadges.tsx`, `charts/ChartWithSource.tsx`

## États & erreurs

- Loading: skeleton pour le chart
- Error: message avec retry
- Empty: si pas de données, "Pas de données macro disponibles"
- Partial: afficher badges même si chart échoue

## Tests

- Gherkin:

```
Feature: Macro
  Scenario: Affichage du snapshot macro
    Given je suis sur la page Macro
    When la page charge
    Then je vois un chart avec zscores GRW/INF/POL/USD/CMD
    And les badges montrent les valeurs actuelles
    And la source et timestamp sont visibles
    And zscores sont dans [-3, +3]
```

- Unit front/back + e2e smoke

## Exemples

- Requête:
```bash
curl -s "http://localhost:8050/api/macro/snapshot"
```

- Réponse (tronquée):

```json
{
  "asof_date": "2025-10-31",
  "zscores": {
    "GRW": 1.2,
    "INF": -0.5,
    "POL": 0.8,
    "USD": -1.1,
    "CMD": 0.3
  },
  "components": {
    "GDP": 2.1,
    "CPI": 2.5
  },
  "source": "FRED/indicators",
  "created_at": "2025-10-31T12:00:00Z",
  "hash": "..."
}
```
