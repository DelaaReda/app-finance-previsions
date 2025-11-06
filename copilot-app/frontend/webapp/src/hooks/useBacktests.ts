import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { client } from '@/api/client';
import type { BacktestsResponse } from '@/types/backtests';
import { validateData, BacktestsResponseSchema, logValidationSuccess } from '@/lib/zodWrapper';

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
  const basePath = '/api/backtests';
  const key = queryString ? `${basePath}?${queryString}` : basePath;

  return useQuery<BacktestsResponse>({
    queryKey: ['backtests', queryString],
    queryFn: async () => {
      const response = await client.get<BacktestsResponse>(key);

      // Validate response schema
      const validated = validateData(response, BacktestsResponseSchema);
      logValidationSuccess('Backtests', validated.equity_curve.length);

      return validated;
    },
    keepPreviousData: true,
  });
}
