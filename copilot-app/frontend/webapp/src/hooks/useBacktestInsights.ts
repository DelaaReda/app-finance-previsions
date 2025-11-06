import { useQuery } from '@tanstack/react-query';
import { fetchBacktestInsights } from '@/services/copilot';
import type { BacktestParams, BacktestSummary } from '@/services/backtests';

type BacktestInsightsInput = {
  summary: BacktestSummary;
  params: BacktestParams;
  question?: string;
};

export function useBacktestInsights(input: BacktestInsightsInput | null, enabled = true) {
  return useQuery({
    queryKey: ['backtest-insights', input],
    queryFn: async () => {
      if (!input) return { text: '' };
      return fetchBacktestInsights(input);
    },
    enabled: Boolean(input && enabled),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}
