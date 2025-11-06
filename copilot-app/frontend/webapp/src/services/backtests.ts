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

