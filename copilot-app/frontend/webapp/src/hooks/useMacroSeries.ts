import { keepPreviousData, useQuery, type UseQueryResult } from '@tanstack/react-query';
import { api } from '@/api/client';
import { qk } from '@/lib/keys';
import { adaptMacroSeries } from '@/lib/adapters';
import type { MacroSeriesMap } from '@/types/macro';
import { ensureArray } from '@/lib/safe';

export function useMacroSeries(ids: string[]): UseQueryResult<MacroSeriesMap>;
export function useMacroSeries(ids: { ids: string[] }): UseQueryResult<MacroSeriesMap>;
export function useMacroSeries(arg: any): UseQueryResult<MacroSeriesMap> {
  const normalizedIds = Array.isArray(arg) ? ensureArray(arg) : ensureArray(arg?.ids);

  return useQuery<MacroSeriesMap>({
    queryKey: qk.macroSeries(normalizedIds),
    enabled: normalizedIds.length > 0,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
    gcTime: 10 * 60_000,
    queryFn: async () => {
      const data = await api.fetchJson<any>('/macro/series', {
        searchParams: { ids: normalizedIds.join(',') },
      });
      return adaptMacroSeries(data);
    },
  });
}
