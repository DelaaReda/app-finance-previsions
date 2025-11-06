import { API_BASE } from '@/config/env';
import { fetchJson } from '@/lib/fetch';
import { ensureArray } from '@/lib/safe';

export interface BacktestSummary {
  cagr: number;
  maxDD: number;
  winRate: number;
  trades: number;
}

export interface EquityPoint {
  t: string;
  v: number;
}

export interface BacktestResponse {
  summary: BacktestSummary;
  equity: EquityPoint[];
}

export interface BacktestStats {
  cagr?: number;
  maxDrawdown?: number;
  maxDD?: number;
  winRate?: number;
  trades?: number;
}

export interface BacktestSnapshot {
  date: string;
  stats: BacktestStats;
}

export interface BacktestParams {
  rule: string;
  horizon: '1m' | '3m' | '6m';
  lookback: number;
  universe: string[];
}

export async function runBacktest(params: BacktestParams) {
  const qs = new URLSearchParams({
    rule: params.rule,
    horizon: params.horizon,
    lookback: String(params.lookback),
    universe: ensureArray(params.universe).join(','),
  });
  const res = await fetchJson<BacktestResponse>(`${API_BASE}/backtests?${qs.toString()}`);
  return {
    summary: res.summary,
    equity: ensureArray(res.equity),
  };
}

export async function runBacktestVariant(params: Record<string, unknown>) {
  const payload = await fetchJson<{ equityCurve?: EquityPoint[]; stats?: BacktestStats }>(`${API_BASE}/backtests/run`, {
    method: 'POST',
    body: JSON.stringify(params),
  });

  return {
    equityCurve: ensureArray(payload.equityCurve),
    stats: payload.stats ?? {},
  };
}

export async function getBacktestHistory(params: Record<string, unknown>) {
  try {
    const qs = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) continue;
      if (Array.isArray(value)) {
        qs.set(key, value.join(','));
      } else {
        qs.set(key, String(value));
      }
    }
    const res = await fetchJson<BacktestSnapshot[]>(`${API_BASE}/backtests/history?${qs.toString()}`);
    return ensureArray(res);
  } catch {
    return [];
  }
}
