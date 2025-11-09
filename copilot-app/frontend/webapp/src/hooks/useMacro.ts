import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { ensureArray } from '@/lib/safe';

export type MacroFreq = 'daily' | 'weekly' | 'monthly' | 'quarterly';

export type MacroPoint = {
  date: string;
  value: number | null;
};

export type MacroSeries = {
  id: string;
  name?: string | null;
  unit?: string | null;
  frequency?: MacroFreq | null;
  points: MacroPoint[];
};

export type MacroResponse = {
  updated_at?: string | null;
  series: MacroSeries[];
};

export function useMacroSeries(params: {
  ids: string[];
  start?: string;
  end?: string;
  frequency?: MacroFreq;
  collapse?: 'none' | 'eom' | 'eoq' | 'eow';
}) {
  const { ids, start, end, frequency, collapse } = params;
  const searchParams: Record<string, string> = {};

  const list = ensureArray(ids);
  if (!list.length) throw new Error('useMacroSeries requires at least one id');
  searchParams.ids = list.join(',');

  if (start) searchParams.start = start;
  if (end) searchParams.end = end;
  if (frequency) searchParams.frequency = frequency;
  if (collapse && collapse !== 'none') searchParams.collapse = collapse;
  searchParams.format_resp = 'map';  // Explicitly request map format as per FC-API-019

  return useQuery<MacroResponse>({
    queryKey: ['macro-series', list, start ?? '', end ?? '', frequency ?? '', collapse ?? ''] as const,
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const json = await api.fetchJson<any>('/api/macro/series', { searchParams });
      const rawData = json?.data ?? json;

      // Handle snapshot data (array of objects with metrics as keys)
      if (Array.isArray(rawData) && rawData.length > 0 && !rawData[0]?.id && !rawData[0]?.points) {
        const snapshot = rawData[0]; // First (and likely only) snapshot
        const now = new Date().toISOString().slice(0, 10);

        // Convert snapshot to series format - return ALL metrics available
        const series: MacroSeries[] = Object.entries(snapshot)
          .filter(([key, value]) => typeof value === 'number')
          .map(([key, value]) => ({
            id: key,
            name: key.replace(/_/g, ' ').toUpperCase(),
            unit: key.includes('prob') || key.includes('rate') ? '%' : null,
            frequency: 'daily' as MacroFreq,
            points: [{ date: now, value: value as number }],
          }));

        // Note: Ignoring requested IDs because snapshot doesn't use FRED IDs
        return {
          updated_at: json?.updated_at ?? null,
          series,
        };
      }

      // Handle normal time series data
      const series = ensureArray(json?.series ?? json?.items ?? json).map((serie: any) => ({
        id: String(serie?.id ?? ''),
        name: serie?.name ?? serie?.title ?? serie?.id ?? null,
        unit: serie?.unit ?? null,
        frequency: (serie?.frequency ?? serie?.freq ?? null) as MacroFreq | null,
        points: ensureArray(serie?.points ?? serie?.data ?? []).map((point: any) => ({
          date: String(point?.date ?? point?.time ?? point?.t ?? ''),
          value: point?.value == null ? null : Number(point.value),
        })),
      }));

      return {
        updated_at: json?.updated_at ?? null,
        series,
      };
    },
  });
}
