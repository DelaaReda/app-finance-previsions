import { useQuery } from '@tanstack/react-query';
import { getBacktestHistory } from '@/services/backtests';
import { ensureArray } from '@/lib/safe';

type HistoryKey = {
  rule: string;
  horizon: string;
  lookback: number;
  universe: string[];
};

export function useBacktestHistory(params: HistoryKey, enabled = true) {
  const keyUniverse = [...ensureArray(params.universe)].sort().join(',');

  return useQuery({
    queryKey: ['backtest-history', params.rule, params.horizon, params.lookback, keyUniverse],
    queryFn: async () =>
      getBacktestHistory({
        rule: params.rule,
        horizon: params.horizon,
        lookback: params.lookback,
        universe: params.universe,
        limit: 60,
      }),
    enabled,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
    select: (data) => ensureArray(data),
  });
}
