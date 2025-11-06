import { useQuery } from '@tanstack/react-query';
import { fetchAutoBacktestPresets, AutoPreset } from '@/services/copilotPresets';

export function useAutoPresets(
  seed?: { universe?: string[]; target?: 'growth' | 'value' | 'balanced' },
  enabled = false
) {
  return useQuery<AutoPreset[]>({
    queryKey: ['auto-presets', seed],
    queryFn: () => fetchAutoBacktestPresets(seed),
    enabled,
    staleTime: 60_000,
  });
}
