import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { client } from '@/api/client';
import { adaptForecasts } from '@/lib/adapters';
import { ensureArray } from '@/lib/safe';
import type { Direction, ForecastItem, ForecastsResponse, Horizon } from '@/types/forecast';

export type ForecastsParams = {
  tickers?: string[];
  horizons?: Horizon[];
  themes?: string[];
  /** Legacy aliases */
  horizon?: Horizon | string;
  universe?: string[];
  limit?: number;
  offset?: number;
  since?: string;
  sort?: string;
};

function buildSearchParams(params: ForecastsParams): string {
  const sp = new URLSearchParams();
  const tickers = params.tickers?.length ? params.tickers : params.universe;
  const horizons = params.horizons?.length ? params.horizons : params.horizon ? [params.horizon as Horizon] : undefined;

  if (tickers?.length) sp.set('tickers', tickers.join(','));
  if (horizons?.length) sp.set('horizons', horizons.join(','));
  if (params.themes?.length) sp.set('themes', params.themes.join(','));
  if (params.limit != null) sp.set('limit', String(params.limit));
  if (params.offset != null) sp.set('offset', String(params.offset));
  if (params.since) sp.set('since', params.since);
  if (params.sort) sp.set('sort', params.sort);
  return sp.toString();
}

function normalizeDirection(direction?: string | null): Direction {
  if (direction === 'up' || direction === 'down') return direction;
  if (direction === 'flat') return 'neutral';
  return 'neutral';
}

/**
 * Fetch forecasts response (metadata + items) using the canonical contract.
 */
export function useForecasts(params: ForecastsParams = {}): UseQueryResult<ForecastsResponse> {
  const queryString = buildSearchParams(params);
  const basePath = '/api/forecasts';
  const key = queryString ? `${basePath}?${queryString}` : basePath;

  return useQuery<ForecastsResponse>({
    queryKey: ['forecasts', queryString],
    queryFn: async () => {
      const raw = await client.get<any>(key);
      const items = adaptForecasts(raw).map((item) => ({
        ...item,
        direction: normalizeDirection(item.direction),
      }));

      return {
        updated_at: raw?.updated_at ?? raw?.data?.updated_at ?? null,
        request_id: raw?.request_id ?? raw?.data?.request_id ?? null,
        count: raw?.count ?? raw?.data?.count ?? items.length,
        items,
      } satisfies ForecastsResponse;
    },
    keepPreviousData: true,
  });
}

// ---------------------------------------------------------------------------
// Forecast matrix (multi-horizon) support (legacy helper kept for dashboards)
// ---------------------------------------------------------------------------

export type MatrixHorizon = '1m' | '3m' | '6m' | '12m';

export interface MatrixForecastItem {
  kind?: 'stock' | 'etf' | 'index' | string;
  symbol: string;
  name?: string | null;
  horizon: MatrixHorizon;
  score: number;
  direction: Direction;
  confidence?: number | null;
  expected_return_pct?: number | null;
  spark?: number[] | null;
  updated_at?: string | null;
}

export interface ForecastsMatrixResponse {
  updated_at?: string | null;
  items: MatrixForecastItem[];
}

export type ForecastMatrixRow = {
  symbol: string;
  name: string;
  cells: Partial<Record<MatrixHorizon, MatrixForecastItem>>;
};

export function useForecastMatrix(params: { universe: string[]; horizons: MatrixHorizon[] }): UseQueryResult<ForecastsMatrixResponse> {
  const universe = ensureArray(params.universe);
  const horizons = ensureArray(params.horizons);
  const searchParams = new URLSearchParams();
  if (universe.length) searchParams.set('tickers', universe.join(','));
  if (horizons.length) searchParams.set('horizons', horizons.join(','));

  const basePath = '/api/forecasts';
  const key = `${basePath}?${searchParams.toString()}`;

  return useQuery<ForecastsMatrixResponse>({
    queryKey: ['forecasts-matrix', universe.join(','), horizons.join(',')],
    queryFn: async () => {
      const raw = await client.get<any>(key);
      const items = adaptForecasts(raw).map((item) => ({
        kind: raw?.kind ?? undefined,
        symbol: item.ticker,
        name: item.name ?? item.ticker,
        horizon: (item.horizon as MatrixHorizon) ?? '1m',
        score: item.score,
        direction: normalizeDirection(item.direction),
        confidence: item.confidence ?? null,
        expected_return_pct: item.expected_return_pct ?? null,
        spark: item.sparkline?.map((point) => point.value ?? 0) ?? null,
        updated_at: item.forecasted_at ?? item.updatedAt ?? null,
      }));

      return {
        updated_at: raw?.updated_at ?? raw?.data?.updated_at ?? null,
        items,
      } satisfies ForecastsMatrixResponse;
    },
    keepPreviousData: true,
  });
}

export function buildForecastMatrix(items: MatrixForecastItem[], horizons: MatrixHorizon[]): ForecastMatrixRow[] {
  const rowsMap = new Map<string, ForecastMatrixRow>();

  ensureArray(items).forEach((item) => {
    const row = rowsMap.get(item.symbol) ?? {
      symbol: item.symbol,
      name: item.name || item.symbol,
      cells: {},
    };
    row.cells[item.horizon] = item;
    rowsMap.set(item.symbol, row);
  });

  const rows = Array.from(rowsMap.values());

  const score = (row: ForecastMatrixRow) => {
    const values = horizons
      .map((h) => row.cells[h]?.score)
      .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    if (!values.length) return Number.NEGATIVE_INFINITY;
    return values.reduce((acc, curr) => acc + curr, 0) / values.length;
  };

  rows.sort((a, b) => score(b) - score(a));

  return rows;
}
