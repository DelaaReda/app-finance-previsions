export type BacktestParams = {
  rule: 'momentum' | 'meanrev' | 'carry';
  horizon: '1m' | '3m' | '6m';
  lookback: number;
  universe: string[];
};
export type AutoPreset = BacktestParams & { label: string };

const API_BASE =
  (import.meta as any)?.env?.VITE_API_BASE_URL ??
  (import.meta as any)?.env?.VITE_API ??
  '/api';

export async function fetchAutoBacktestPresets(seed?: {
  universe?: string[];
  target?: 'growth' | 'value' | 'balanced';
}): Promise<AutoPreset[]> {
  // 1) attempt server
  try {
    const res = await fetch(`${API_BASE}/copilot/presets/backtests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(seed ?? {}),
    });
    if (res.ok) {
      const json = await res.json();
      if (Array.isArray(json) && json.length) {
        return json
          .map((p: any) => ({
            label: String(p?.label ?? 'Preset'),
            rule: (p?.rule ?? 'momentum') as AutoPreset['rule'],
            horizon: (p?.horizon ?? '1m') as AutoPreset['horizon'],
            lookback: Number.isFinite(p?.lookback) ? Number(p.lookback) : 180,
            universe: Array.isArray(p?.universe) ? p.universe : ['SPY', 'QQQ'],
          }))
          .slice(0, 5);
      }
    }
  } catch (e) {
    // noop -> fallback
  }

  // 2) fallback local (5 clean combos)
  const pick = (...xs: string[]) => xs.filter(Boolean);

  const presets: AutoPreset[] = [
    {
      label: 'Auto: Momentum Core (SPY,QQQ)',
      rule: 'momentum',
      horizon: '1m',
      lookback: 180,
      universe: pick('SPY', 'QQQ'),
    },
    {
      label: 'Auto: Momentum Growth (QQQ,NVDA)',
      rule: 'momentum',
      horizon: '3m',
      lookback: 240,
      universe: pick('QQQ', 'NVDA'),
    },
    {
      label: 'Auto: MeanRev Bluechips (AAPL,MSFT)',
      rule: 'meanrev',
      horizon: '1m',
      lookback: 120,
      universe: pick('AAPL', 'MSFT'),
    },
    {
      label: 'Auto: Carry LargeCap (SPY,DIA)',
      rule: 'carry',
      horizon: '3m',
      lookback: 360,
      universe: pick('SPY', 'DIA'),
    },
    {
      label: 'Auto: Momentum Mixed (SPY,QQQ,AAPL)',
      rule: 'momentum',
      horizon: '6m',
      lookback: 360,
      universe: pick('SPY', 'QQQ', 'AAPL'),
    },
  ];

  if (seed?.target === 'growth') {
    return presets.sort((a) => (a.universe.includes('QQQ') || a.universe.includes('NVDA') ? -1 : 1));
  }
  if (seed?.target === 'value') {
    return presets.sort((a) => (a.universe.includes('DIA') ? -1 : 1));
  }
  return presets;
}
