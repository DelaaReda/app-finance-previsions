import { keepPreviousData, useQuery, type UseQueryResult } from '@tanstack/react-query';
import { api } from '@/api/client';
import { qk } from '@/lib/keys';
import { adaptMacroSeries } from '@/lib/adapters';
import type { MacroSeriesMap } from '@/types/macro';
import { ensureArray } from '@/lib/safe';

export type MacroRange = '1y' | '3y' | '5y' | '10y' | 'max';
export type MacroFreq = 'daily' | 'weekly' | 'monthly' | 'quarterly';

export interface MacroDrilldownPoint {
  date: string;
  value: number | null;
}

export interface MacroDrilldownSeries {
  id: string;
  title?: string | null;
  unit?: string | null;
  freq?: MacroFreq | null;
  data: MacroDrilldownPoint[];
}

export interface MacroDrilldownResponse {
  updated_at?: string | null;
  series: MacroDrilldownSeries[];
}

export function useMacroSeries(ids: string[]): UseQueryResult<MacroSeriesMap>;
export function useMacroSeries(params: { ids: string[]; range: MacroRange; freq?: MacroFreq }): UseQueryResult<MacroDrilldownResponse>;
export function useMacroSeries(arg: any): UseQueryResult<MacroSeriesMap | MacroDrilldownResponse> {
  if (Array.isArray(arg)) {
    const normalizedIds = ensureArray(arg);
    return useQuery<MacroSeriesMap>({
      queryKey: qk.macroSeries(normalizedIds),
      enabled: normalizedIds.length > 0,
      placeholderData: keepPreviousData,
      staleTime: 60_000,
      gcTime: 10 * 60_000,
      queryFn: async () => {
        const json = await api.fetchJson<any>('/api/macro/series', {
          searchParams: { ids: normalizedIds.join(',') },
        });

        const rawData = json?.data ?? json;

        // Handle snapshot data (array of objects with metrics as keys)
        if (Array.isArray(rawData) && rawData.length > 0 && !rawData[0]?.id) {
          const snapshot = rawData[0];
          const now = new Date().toISOString().slice(0, 10);
          const result: MacroSeriesMap = {};

          // Convert snapshot to MacroSeriesMap format - return ALL metrics
          Object.entries(snapshot).forEach(([key, value]) => {
            if (typeof value === 'number') {
              result[key] = [{ date: now, value }];
            }
          });

          return result;
        }

        // Use existing adapter for normal time series data
        return adaptMacroSeries(json);
      },
    });
  }

  const { ids, range, freq } = arg ?? {};
  const normalizedIds = ensureArray(ids);

  return useQuery<MacroDrilldownResponse>({
    queryKey: ['macro-series-drilldown', [...normalizedIds].sort().join(','), range ?? null, freq ?? null] as const,
    enabled: normalizedIds.length > 0 && Boolean(range),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
    gcTime: 10 * 60_000,
    queryFn: async () => {
      const searchParams: Record<string, string> = {
        ids: normalizedIds.join(','),
        range,
      };
      if (freq) searchParams.freq = freq;

      const json = await api.fetchJson<any>('/api/macro/series', { searchParams });
      const rawData = json?.data ?? json;

      // Handle snapshot data (array of objects with metrics as keys)
      if (Array.isArray(rawData) && rawData.length > 0 && !rawData[0]?.id && !rawData[0]?.points && !rawData[0]?.data) {
        const snapshot = rawData[0];
        const now = new Date().toISOString().slice(0, 10);

        // Convert snapshot to series format - return ALL metrics available
        const series: MacroDrilldownSeries[] = Object.entries(snapshot)
          .filter(([key, value]) => typeof value === 'number')
          .map(([key, value]) => ({
            id: key,
            title: key.replace(/_/g, ' ').toUpperCase(),
            unit: key.includes('prob') || key.includes('rate') ? '%' : null,
            freq: 'daily' as any,
            data: [{ date: now, value: value as number }],
          }));

        return {
          updated_at: json?.updated_at ?? null,
          series,
        };
      }

      // Handle normal time series data
      const series = ensureArray<MacroDrilldownSeries>(json?.series ?? json?.items ?? json).map((serie) => ({
        ...serie,
        data: ensureArray<MacroDrilldownPoint>(serie.data ?? serie.points ?? []).map((point) => ({
          date: String(point.date),
          value: point.value == null ? null : Number(point.value),
        })),
      }));

      return {
        updated_at: json?.updated_at ?? null,
        series,
      };
    },
  });
}

export function toWideTable(series: MacroDrilldownSeries[], { normalize = false }: { normalize?: boolean } = {}) {
  const dates = new Set<string>();
  ensureArray(series).forEach((serie) => {
    ensureArray(serie.data).forEach((point) => dates.add(point.date));
  });
  const orderedDates = Array.from(dates).sort();

  const bases: Record<string, number | null> = {};
  if (normalize) {
    for (const serie of series) {
      const base = ensureArray(serie.data).find((point) => typeof point.value === 'number');
      bases[serie.id] = base?.value ?? null;
    }
  }

  return orderedDates.map((date) => {
    const row: Record<string, any> = { date };
    for (const serie of series) {
      const value = ensureArray(serie.data).find((point) => point.date === date)?.value ?? null;
      if (normalize && typeof value === 'number' && typeof bases[serie.id] === 'number' && bases[serie.id]! !== 0) {
        row[serie.id] = (value / bases[serie.id]!) * 100;
      } else {
        row[serie.id] = value;
      }
    }
    return row;
  });
}
