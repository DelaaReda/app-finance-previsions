import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { ensureArray } from '@/lib/safe';

export type MacroId = string;
export type RangeOpt = '1y' | '3y' | '5y' | 'max';

export interface RawPoint {
  date: string;
  value: number | string | null;
}

export interface RawSeries {
  id: MacroId;
  name?: string | null;
  unit?: string | null;
  frequency?: string | null;
  points?: RawPoint[] | null;
  updated_at?: string | null;
}

export interface MacroSeries {
  id: MacroId;
  name: string;
  unit?: string;
  frequency?: string;
  updatedAt?: string | null;
  points: { date: string; value: number }[];
}

function toNumber(input: unknown): number | undefined {
  if (input == null) return undefined;
  const value = typeof input === 'string' ? Number(input) : (input as number);
  if (!Number.isFinite(value)) return undefined;
  return value;
}

function normalizeSeries(series: RawSeries): MacroSeries {
  const points = ensureArray(series.points)
    .map((point) => ({
      date: String(point.date),
      value: toNumber(point.value),
    }))
    .filter((point): point is { date: string; value: number } => typeof point.value === 'number');

  points.sort((a, b) => a.date.localeCompare(b.date));

  return {
    id: series.id,
    name: series.name || series.id,
    unit: series.unit ?? undefined,
    frequency: series.frequency ?? undefined,
    updatedAt: series.updated_at ?? null,
    points,
  };
}

export interface MacroSeriesResponse {
  items: MacroSeries[];
  byId: Map<MacroId, MacroSeries>;
}

export function useMacroSeries(params: { ids: MacroId[]; range?: RangeOpt }) {
  const ids = ensureArray(params.ids);
  const range = params.range ?? '3y';

  return useQuery<MacroSeriesResponse>({
    queryKey: ['macro-series', ids, range] as const,
    queryFn: async () => {
      const data = await api.fetchJson<any>('/macro/series', {
        searchParams: {
          ids: ids.join(','),
          range,
        },
      });

      const items = ensureArray<RawSeries>(data?.items ?? data?.data ?? data).map(normalizeSeries);
      const byId = new Map<MacroId, MacroSeries>();
      for (const item of items) byId.set(item.id, item);
      return { items, byId };
    },
  });
}

export function lastDelta(series?: MacroSeries): { last?: number; prev?: number; delta?: number } {
  if (!series || series.points.length === 0) return {};
  const last = series.points[series.points.length - 1]?.value;
  const prev = series.points[series.points.length - 2]?.value;
  if (typeof last !== 'number' || typeof prev !== 'number') {
    return { last, prev };
  }
  return { last, prev, delta: last - prev };
}

export interface MacroSignal {
  key: string;
  name: string;
  severity: 'info' | 'low' | 'medium' | 'high';
  value?: number | string | null;
  description?: string | null;
  metric_id?: MacroId | null;
  updated_at?: string | null;
}

export function useMacroSignals() {
  return useQuery({
    queryKey: ['macro-signals'],
    queryFn: async () => {
      const data = await api.fetchJson<any>('/macro/signals');
      return {
        updatedAt: data?.updated_at ?? null,
        signals: ensureArray<MacroSignal>(data?.signals),
      };
    },
  });
}
