import { useQuery } from '@tanstack/react-query';
import { getMacroSeries, MacroSeries } from '@/services/macro';
import { ensureArray } from '@/lib/safe';
import { NET } from '@/config/env';

export function useMacroSeries(codes: string[]) {
  return useQuery<MacroSeries[]>({
    queryKey: ['macro-series', ensureArray(codes).sort().join(',')],
    queryFn: () => getMacroSeries(codes),
    staleTime: NET.staleMacroMs,
    gcTime: 15 * 60_000,
    retry: NET.retry,
    select: (arr) => ensureArray(arr),
  });
}

