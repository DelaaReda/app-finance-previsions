import { useQuery } from '@tanstack/react-query';
import type { BacktestParams, BacktestResponse } from '@/services/backtests';
import { runBacktest } from '@/services/backtests';

export function useBacktest(params: BacktestParams, enabled = true) {
  const keyUniverse = [...params.universe].sort().join(',');
  return useQuery<BacktestResponse>({
    queryKey: ['backtest', params.rule, params.horizon, params.lookback, keyUniverse],
    queryFn: () => runBacktest(params),
    enabled,
    staleTime: 60_000,
  });
}
