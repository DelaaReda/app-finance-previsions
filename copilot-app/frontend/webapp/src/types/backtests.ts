export type BacktestsResponse = {
  request_id?: string | null;
  updated_at?: string | null;
  params: {
    strategy: string;
    universe?: string | null;
    benchmark?: string | null;
    horizon?: 'short' | 'medium' | 'long' | null;
  };
  kpis: {
    cagr_pct: number;
    sharpe: number;
    sortino: number;
    max_drawdown_pct: number;
    win_rate_pct: number;
    volatility_pct: number;
    exposure_pct?: number;
    avg_trade_pct?: number;
  };
  equity_curve: { date: string; strategy: number | null; benchmark?: number | null }[];
  drawdowns?: { date: string; dd_pct: number | null }[];
  monthly_returns?: { month: string; pct: number | null }[];
  trades_sample?: { enter: string; exit: string; ticker: string; ret_pct: number | null }[];
};
