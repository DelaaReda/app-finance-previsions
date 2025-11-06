export const qk = {
  forecasts: (horizon: string, universe: string[], themes?: string[]) => [
    'forecasts',
    horizon,
    [...universe].sort().join(','),
    (themes ?? []).sort().join(','),
  ],
  macroSeries: (ids: string[]) => ['macro-series', [...ids].sort().join(',')],
  news: (universe: string[], limit: number) => ['news', [...universe].sort().join(','), limit],
  performanceMatrix: (
    horizons: string[],
    tickers: string[],
    sectors: string[],
    themes: string[],
  ) => [
    'performance-matrix',
    [...horizons].sort().join(','),
    [...tickers].sort().join(','),
    [...sectors].sort().join(','),
    [...themes].sort().join(','),
  ],
  forecastMatrix: (universe: string[], horizons: string[]) => [
    'forecast-matrix',
    [...universe].sort().join(','),
    [...horizons].sort().join(','),
  ],
} as const;
