import { API_BASE } from '@/config/env';
import { fetchJson } from '@/lib/fetch';
import { ensureArray } from '@/lib/safe';

export type Horizon = '1m' | '3m' | '6m';
export type Dir = 'up' | 'down';

export interface ForecastItem {
  id: string;
  type: 'ticker';
  symbol: string;
  name?: string;
  horizon: Horizon;
  score: number;
  dir: Dir;
  conf: number;
  expected_return: number;
  model?: { name: string; version?: string };
  generated_at?: string;
}

export async function getForecasts(params: { horizon: Horizon; tickers: string[] }) {
  const qs = new URLSearchParams({
    horizon: params.horizon,
    tickers: ensureArray(params.tickers).join(','),
  });
  const data = await fetchJson<unknown>(`${API_BASE}/forecasts?${qs.toString()}`);
  return ensureArray(data as ForecastItem[]);
}

export interface ForecastDetail extends ForecastItem {
  rationale?: string;
  feature_importances?: Array<{ name: string; weight: number }>;
  series?: Array<{ t: string; v: number }>;
}

export async function getForecastDetail(id: string) {
  return await fetchJson<ForecastDetail>(`${API_BASE}/forecasts/${encodeURIComponent(id)}`);
}

