import { keepPreviousData, useQuery, type UseQueryResult } from '@tanstack/react-query';
import { api } from '@/api/client';
import { qk } from '@/lib/keys';
import { adaptForecasts } from '@/lib/adapters';
import type { ForecastItem, Horizon, Direction } from '@/types/forecast';
import { ensureArray } from '@/lib/safe';

type LegacyHorizon = '1m' | '3m' | '6m';

export interface ForecastsParams {
  horizon: Horizon;
  universe: string[];
  themes?: string[];
}

function normalizeHorizon(value: string): Horizon {
  const map: Record<string, Horizon> = {
    '1m': 'short',
    '1d': 'short',
    short: 'short',
    '3m': 'medium',
    medium: 'medium',
    '6m': 'long',
    long: 'long',
  };
  return map[value] ?? 'short';
}

function normalizeUniverse(value: string[] | string | undefined): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

export function useForecasts(params: ForecastsParams): UseQueryResult<ForecastItem[]>;
export function useForecasts(horizon: LegacyHorizon | Horizon, tickers: string[]): UseQueryResult<ForecastItem[]>;
export function useForecasts(arg1: any, arg2?: any): UseQueryResult<ForecastItem[]> {
  const config: ForecastsParams =
    typeof arg1 === 'object' && arg1 !== null && !Array.isArray(arg1)
      ? {
          horizon: normalizeHorizon(arg1.horizon),
          universe: normalizeUniverse(arg1.universe),
          themes: ensureArray(arg1.themes),
        }
      : {
          horizon: normalizeHorizon(String(arg1)),
          universe: normalizeUniverse(arg2),
          themes: [],
        };

  return useQuery<ForecastItem[]>({
    queryKey: qk.forecasts(config.horizon, config.universe, config.themes),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    queryFn: async () => {
      const data = await api.fetchJson<any>('/forecasts', {
        searchParams: {
          horizon: config.horizon,
          universe: config.universe.length ? config.universe.join(',') : undefined,
          themes: config.themes?.length ? config.themes.join(',') : undefined,
        },
      });
      return adaptForecasts(data);
    },
  });
}

// ---------------------------------------------------------------------------
// Forecast matrix (multi-horizon) support
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
  expected_return?: number | null;
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

  return useQuery<ForecastsMatrixResponse>({
    queryKey: qk.forecastMatrix(universe, horizons),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    queryFn: async () => {
      const data = await api.fetchJson<any>('/forecasts', {
        searchParams: {
          universe: universe.length ? universe.join(',') : undefined,
          horizons: horizons.length ? horizons.join(',') : undefined,
        },
      });

      return {
        updated_at: data?.updated_at ?? null,
        items: ensureArray<MatrixForecastItem>(data?.items ?? data),
      };
    },
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
