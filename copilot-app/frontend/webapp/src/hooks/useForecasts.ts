import { useQuery } from '@tanstack/react-query';
import { getForecasts, ForecastItem, Horizon } from '@/services/forecasts';
import { ensureArray } from '@/lib/safe';
import { NET } from '@/config/env';

export function useForecasts(horizon: Horizon, tickers: string[]) {
  return useQuery<ForecastItem[]>({
    queryKey: ['forecasts', horizon, ensureArray(tickers).sort().join(',')],
    queryFn: () => getForecasts({ horizon, tickers }),
    staleTime: NET.staleForecastsMs,
    gcTime: 5 * 60_000,
    retry: NET.retry,
    select: (arr) => ensureArray(arr),
  });
}

