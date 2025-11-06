export const qk = {
  forecasts: (horizon: string, universe: string[], themes?: string[]) => [
    'forecasts',
    horizon,
    [...universe].sort().join(','),
    (themes ?? []).sort().join(','),
  ],
  macroSeries: (ids: string[]) => ['macro-series', [...ids].sort().join(',')],
  news: (universe: string[], limit: number) => ['news', [...universe].sort().join(','), limit],
} as const;
