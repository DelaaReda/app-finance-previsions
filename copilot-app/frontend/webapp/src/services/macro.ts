import { API_BASE } from '@/config/env';
import { fetchJson } from '@/lib/fetch';
import { ensureArray } from '@/lib/safe';

export interface MacroPoint {
  t: string;
  v: number;
}

export interface MacroSeries {
  code: string;
  name?: string;
  points: MacroPoint[];
}

export async function getMacroSeries(codes: string[]) {
  const qs = new URLSearchParams({ codes: ensureArray(codes).join(',') });
  const data = await fetchJson<unknown>(`${API_BASE}/macro/series?${qs.toString()}`);
  const arr = ensureArray(data as MacroSeries[]);
  return arr.map((series) => ({
    ...series,
    points: ensureArray(series.points),
  }));
}

