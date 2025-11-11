# Pack: Templates de Dashboards (Mantine + Tremor) — Guide d'utilisation

Ce document explique comment utiliser le pack "templates de dashboards" (Mantine + Tremor) que j'ai déposé dans le canvas.
L'objectif : fournir des templates réutilisables, config-driven, sans mocks — les widgets consomment directement les hooks existants.

## Ce que contient le pack

- Un renderer de template et une page dédiée : `/dashboards/:slug?` (DashboardsPage / DashboardsRenderer).
- Deux templates prêts à l'emploi : `market-overview`, `macro-pulse`.
- Widgets réutilisables (Metric, Area/Line, BarList, Donut, Table) implémentés avec Tremor + Mantine.
- Un panneau de contrôle (horizon, univers, macro-ids, thèmes) qui re-render proprement.
- Contrats types : `DashboardTemplate`, `WidgetConfig` (voir exemple plus bas).

## Principes d'utilisation

1. Aucun mock : les widgets appellent directement les hooks de données existants :
   - `useForecasts(...)`
   - `useMacroSeries(...)`
   - `useNews(...)`

2. Config-driven : un dashboard est simplement un objet `DashboardTemplate` qui décrit les sections et widgets.

3. Never-empty : tous les widgets utilisent `@/lib/safe` (`ensureArray`, `nn`) et affichent un `EmptyState` / skeleton si pas de données.

## Où coller les fichiers

Coller les fichiers déposés dans le canvas en respectant les chemins fournis (ex. `src/pages/Dashboards.tsx`, `src/ui/*`, `src/templates/*`).

## Ajouter la route

DANS `src/App.tsx` :

```tsx
<Route path="/dashboards/:slug?" element={<DashboardsPage />} />
```

## Contrat minimal attendu pour les hooks

Assure-toi que les hooks suivants existent et respectent ces signatures (ou adaptent-toi en créant un petit adapter) :

- `useMacroSeries(ids: string[])` → retourne `UseQueryResult<SeriesPoint[], Error>` où `SeriesPoint = { date: string; value: number }`.
- `useForecasts(options: { horizon: string; universe: string[]; themes?: string[] })` → retourne `UseQueryResult<ForecastItem[], Error>`.
- `useNews(options: { universe?: string[]; limit?: number })` → retourne `UseQueryResult<NewsArticle[], Error>`.

Si tes hooks ont des signatures différentes, crée un petit adapter (ex: `hooks/useForecastsAdapter.ts`) pour normaliser l'API vers ce que les widgets attendent.

## Exemple `DashboardTemplate` (JSON)

```json
{
  "slug": "market-overview",
  "title": "Market Overview",
  "controls": {
    "horizon": "1d",
    "universe": ["SPY","QQQ"],
    "macroIds": ["CPIAUCSL","VIXCLS"]
  },
  "sections": [
    {
      "id": "kpis",
      "widgets": [
        { "type": "metric", "props": { "source": "forecasts.count" } },
        { "type": "metric", "props": { "source": "backtests.summary.cagr" } }
      ]
    },
    {
      "id": "signals",
      "widgets": [
        { "type": "barlist", "props": { "source": "forecasts.top5" } },
        { "type": "donut", "props": { "source": "forecasts.directional" } }
      ]
    }
  ]
}
```

Les `source` sont résolus par le renderer : `forecasts.top5` → appelle `useForecasts` et transforme le résultat en `BarList` friendly.

## Ajouter un widget custom

1. Créer un composant sous `src/components/widgets/YourWidget.tsx` qui accepte `props: { data: any; controls: any }`.
2. Enregistrer le widget dans le mapping `src/templates/widgetRegistry.ts` :

```ts
export const widgetRegistry = {
  metric: MetricWidget,
  barlist: BarListWidget,
  donut: DonutWidget,
  your_widget: YourWidget,
}
```

3. Mettre à jour le template JSON pour utiliser `"type": "your_widget"`.

## Panneau de contrôle (Control Panel)

Le panneau publie un objet `controls` (horizon, universe, macroIds, theme). Le renderer passe `controls` aux widgets en tant que prop. Les widgets doivent rester purs et rerender sur `controls` change.

## Tests & validations rapides

1. `pnpm run -s typecheck` — vérifier qu'il n'y a aucune erreur TypeScript.
2. Lancer la page `/dashboards/market-overview` et vérifier :
   - Les widgets s'affichent (ou un EmptyState si pas de données).
   - Les contrôles provoquent un rerender (changer horizon/universe).
3. Capturer 1 screenshot par template et déposer dans `proofs/DASHBOARDS/`

## Exemple rapide d'adapter si hooks diffèrent

Si `useForecasts` retourne `{ rows: ForecastItem[] }` au lieu d'un array, ajoute un adaptateur :

```ts
export function useForecastsAdapter(opts) {
  const q = useForecastsRaw(opts);
  return { ...q, data: q.data?.rows ?? [] };
}
```

## Liens utiles

- Page renderer: `src/pages/Dashboards.tsx`
- Registry widgets: `src/templates/widgetRegistry.ts`
- Exemples templates: `src/templates/market-overview.json`, `src/templates/macro-pulse.json`

---
Si tu veux que je branche le 3ᵉ template "Stocks Momentum" et un widget Donut secteurs, dis‑le et je pousse les fichiers (template + widget) prêts à brancher.
