import { API_BASE } from '@/config/env';

type CopilotChunk = {
  delta?: string;
  done?: boolean;
  error?: string;
};

export async function askCopilotStream(
  body: { prompt: string; context?: any },
  onDelta: (text: string) => void,
  opts?: { signal?: AbortSignal; onDone?: () => void; onError?: (e: any) => void },
) {
  try {
    const res = await fetch(`${API_BASE}/copilot/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: opts?.signal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`Copilot HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split(/\n\n|\r\n\r\n/);
      buffer = parts.pop() || '';

      for (const chunk of parts) {
        const line = chunk.trim().startsWith('data:')
          ? chunk.trim().replace(/^data:\s*/, '')
          : chunk.trim();
        if (!line) continue;
        try {
          const json = JSON.parse(line) as CopilotChunk;
          if (json.delta) onDelta(json.delta);
          if (json.done) { opts?.onDone?.(); return; }
          if (json.error) throw new Error(json.error);
        } catch {
          onDelta(line);
        }
      }
    }

    opts?.onDone?.();
  } catch (error) {
    opts?.onError?.(error);
    throw error;
  }
}

type BacktestSummary = {
  cagr?: number;
  maxDD?: number;
  winRate?: number;
  trades?: number;
  sharpe?: number;
  calmar?: number;
};

export async function fetchBacktestInsights(args: {
  summary: BacktestSummary;
  params: {
    rule: string;
    horizon: string;
    lookback: number;
    universe: string[];
  };
  question?: string;
}): Promise<{ text: string }> {
  try {
    const res = await fetch(`${API_BASE}/copilot/insights/backtest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(args),
    });

    if (res.ok) {
      const json = await res.json();
      if (typeof json?.text === 'string' && json.text.trim().length > 0) {
        return { text: json.text };
      }
    }
  } catch {
    // Ignore network/API failures → fallback below.
  }

  const s = args.summary ?? {};
  const toPct = (v?: number) =>
    Number.isFinite(v) ? `${((v as number) * 100).toFixed(1)}%` : '—';

  const formatTrades = (v?: number) =>
    Number.isFinite(v) ? String(v) : '—';

  const p = args.params ?? { rule: '—', horizon: '—', lookback: 0, universe: [] };
  const uni = Array.isArray(p.universe) && p.universe.length > 0 ? p.universe.join(', ') : '—';

  const heuristics: string[] = [];
  if (typeof s.cagr === 'number' && s.cagr > 0.12) heuristics.push('Croissance élevée');
  if (typeof s.maxDD === 'number' && s.maxDD < 0.15) heuristics.push('Drawdown contenu');
  if (typeof s.winRate === 'number' && s.winRate > 0.55) heuristics.push('Taux de réussite robuste');

  const fallback = [
    `Aperçu stratégique — règle ${p.rule} (${p.horizon})`,
    '',
    `• Univers évalué : ${uni}`,
    `• Fenêtre de lookback : ${p.lookback} jours`,
    '',
    `Résultats clés`,
    `• CAGR : ${toPct(s.cagr)}`,
    `• MaxDD : ${toPct(s.maxDD)}`,
    `• WinRate : ${toPct(s.winRate)}`,
    `• Nombre de trades : ${formatTrades(s.trades)}`,
    '',
    `Lecture rapide`,
    heuristics.length > 0 ? `• ${heuristics.join(' • ')}` : '• Comportement moyen sans signal saillant',
    '',
    args.question
      ? `Réponse à la question: « ${args.question} » — sur base des métriques ci-dessus, l’algorithme suggère d’analyser la stabilité du drawdown et la sensibilité aux variations d’univers.`
      : `Conseil : valide la robustesse en modifiant l’univers (ex: +AAPL, MSFT) et en testant 3 horizons (1m/3m/6m).`,
  ].join('\n');

  return { text: fallback };
}
