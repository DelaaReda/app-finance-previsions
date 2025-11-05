# Proof — FC-UI-001 — Unwrap frontend API responses

Objectif: corriger l’UI vide alors que la console/Network montre bien des données.

## Commandes

```
curl -s 'http://localhost:5173/api/dashboard/kpis?horizons=short' | jq .
```

Extrait (sample):

```
{
  "ok": true,
  "data": {
    "last_forecast_dt": "20251105",
    "forecasts_count": 12,
    "tickers": 4,
    "horizons": ["1m","1w","1y"],
    "filtered_signals": [
      {"ticker":"AAPL", "composite_score": 0.2363, "reason": "Signal composite"},
      {"ticker":"NVDA", "composite_score": -0.4011, "reason": "Signal composite"}
    ],
    "filtered_risks": [
      {"ticker":"TSLA", "composite_score": -0.52, "reason": "Risque composite"}
    ],
    "generated_at": "2025-11-05T.."
  }
}
```

Après patch côté front (`client.ts`, `services/api.ts`), l’UI lit directement `data.filtered_signals`/`data.filtered_risks` et affiche les cartes Top 3.

Date: 2025-11-05

