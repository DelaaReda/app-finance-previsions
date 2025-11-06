import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { client } from '@/api/client';
import type { BacktestsResponse } from '@/types/backtests';

export type BacktestsParams = {
  strategy: string;
  universe?: string;
  benchmark?: string;
  horizon?: string;
  since?: string;
  until?: string;
};

export function useBacktests(params: BacktestsParams): UseQueryResult<BacktestsResponse> {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value != null && value !== '') sp.set(key, String(value));
  });

  const queryString = sp.toString();
  const key = `/backtests?${queryString}`;

  return useQuery<BacktestsResponse>({
    queryKey: ['backtests', queryString],
    queryFn: () => client.get<BacktestsResponse>(key),
    keepPreviousData: true,
  });
}
