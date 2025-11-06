export type BacktestSummary = {
  cagr?: number;
  maxDD?: number;
  winRate?: number;
  trades?: number;
};

const clamp = (value: number, min = 0, max = 100) => Math.max(min, Math.min(max, value));
const percent = (value?: number) => (Number.isFinite(value ?? NaN) ? (value as number) : 0);

function scoreCAGR(cagr01: number) {
  return clamp((cagr01 * 100 - 0) * (60 / 20) + 40);
}

function scoreDrawdown(drawdown01: number) {
  const dd = Math.abs(drawdown01) * 100;
  return clamp(100 - dd * 1.8);
}

function scoreWinRate(winRate01: number) {
  const win = winRate01 * 100;
  return clamp((win - 50) * 2 + 50);
}

function scoreTrades(trades: number) {
  if (!Number.isFinite(trades) || trades <= 0) return 20;
  if (trades <= 50) return clamp(20 + (trades / 50) * 40);
  return clamp(60 + Math.min(40, ((trades - 50) / 350) * 40));
}

export function robustScore(summary?: BacktestSummary) {
  const sCagr = scoreCAGR(percent(summary?.cagr));
  const sDrawdown = scoreDrawdown(percent(summary?.maxDD));
  const sWin = scoreWinRate(percent(summary?.winRate));
  const sTrades = scoreTrades(summary?.trades ?? 0);

  const total = clamp(sCagr * 0.4 + sDrawdown * 0.3 + sWin * 0.2 + sTrades * 0.1);
  const grade =
    total >= 90 ? 'S' : total >= 80 ? 'A' : total >= 70 ? 'B' : total >= 60 ? 'C' : total >= 50 ? 'D' : 'E';

  return {
    total: Math.round(total),
    parts: {
      CAGR: Math.round(sCagr),
      Drawdown: Math.round(sDrawdown),
      WinRate: Math.round(sWin),
      Trades: Math.round(sTrades),
    },
    grade,
  };
}
