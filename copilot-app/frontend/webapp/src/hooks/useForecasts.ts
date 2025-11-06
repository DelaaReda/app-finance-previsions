import { keepPreviousData, useQuery, type UseQueryResult } from '@tanstack/react-query';
import { api } from '@/api/client';
import { qk } from '@/lib/keys';
import { adaptForecasts } from '@/lib/adapters';
import type { ForecastItem, Horizon } from '@/types/forecast';
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
