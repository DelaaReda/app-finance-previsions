/**
 * Robustness Scoring Library - Finance Copilot
 * Calculates performance metrics for financial forecasts and backtests
 * Task: FC-NEW-021 - ALEX-FINANCE-ANALYST-SUPERMAN-29
 */

export interface BacktestMetrics {
  cagr?: number;          // Compound Annual Growth Rate
  maxDrawdown?: number;   // Maximum drawdown
  winRate?: number;       // Percentage of winning trades
  totalTrades?: number;   // Total number of trades
  sharpeRatio?: number;   // Risk-adjusted return
  volatility?: number;    // Standard deviation of returns
  profitFactor?: number;  // Gross profit / gross loss
  avgReturn?: number;     // Average return per trade
  hitRate?: number;       // Accuracy of direction predictions
  hitRateRecent?: number; // Hit rate for recent period
}

export interface RobustnessScore {
  score: number;          // Overall score (0-1 scale)
  grade: string;          // Letter grade (S, A, B, C, D, E)
  metrics: BacktestMetrics; // Detailed metrics
  breakdown: {
    cagrWeighted: number;
    drawdownWeighted: number;
    winRateWeighted: number;
    tradeCountWeighted: number;
    hitRateWeighted: number;
  };
  confidence: number;     // Confidence in the score
  lastUpdated?: string;   // Timestamp of calculation
}

/**
 * Calculate compound annual growth rate
 * @param initialBalance Starting capital
 * @param finalBalance Ending capital
 * @param years Number of years
 * @returns CAGR as decimal
 */
export function calculateCAGR(initialBalance: number, finalBalance: number, years: number): number {
  if (initialBalance <= 0 || years <= 0) return 0;
  return Math.pow(finalBalance / initialBalance, 1 / years) - 1;
}

/**
 * Calculate maximum drawdown from equity curve
 * @param equityCurve Array of portfolio values over time
 * @returns Max drawdown as decimal
 */
export function calculateMaxDrawdown(equityCurve: number[]): number {
  if (equityCurve.length === 0) return 0;
  
  let peak = equityCurve[0];
  let maxDrawdown = 0;
  
  for (const value of equityCurve) {
    if (value > peak) {
      peak = value;
    }
    const drawdown = (peak - value) / peak;
    if (drawdown > maxDrawdown) {
      maxDrawdown = drawdown;
    }
  }
  
  return maxDrawdown;
}

/**
 * Calculate win rate (percentage of profitable trades)
 * @param returns Array of trade returns
 * @returns Win rate as decimal (0-1)
 */
export function calculateWinRate(returns: number[]): number {
  if (returns.length === 0) return 0;
  
  const profitableTrades = returns.filter(r => r > 0).length;
  return profitableTrades / returns.length;
}

/**
 * Calculate Sharpe ratio (risk-adjusted return)
 * @param returns Array of periodic returns
 * @param riskFreeRate Risk-free rate (default 0.02 for 2% annually)
 * @returns Sharpe ratio
 */
export function calculateSharpeRatio(returns: number[], riskFreeRate: number = 0.02/252): number { // Daily RF rate
  if (returns.length === 0) return 0;
  
  const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const excessReturn = avgReturn - riskFreeRate;
  
  // Calculate volatility (standard deviation)
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
  const volatility = Math.sqrt(variance);
  
  if (volatility === 0) return 0;
  return excessReturn / volatility;
}

/**
 * Calculate profit factor (gross profit / gross loss)
 * @param returns Array of trade returns
 * @returns Profit factor (>= 1.0 is profitable)
 */
export function calculateProfitFactor(returns: number[]): number {
  if (returns.length === 0) return 0;
  
  const profits = returns.filter(r => r > 0).reduce((sum, r) => sum + r, 0);
  const losses = Math.abs(returns.filter(r => r < 0).reduce((sum, r) => sum + r, 0));
  
  if (losses === 0) return profits > 0 ? Infinity : 1;
  return profits / losses;
}

/**
 * Calculate hit rate for direction predictions
 * @param predictions Array of predicted directions (1 for up, -1 for down, 0 for neutral)
 * @param actualReturns Array of actual returns (1 for up, -1 for down, 0 for flat)
 * @returns Hit rate (correct direction predictions) as decimal
 */
export function calculateHitRate(predictions: number[], actualReturns: number[]): number {
  if (predictions.length === 0 || predictions.length !== actualReturns.length) return 0;
  
  const correctPredictions = predictions.filter((pred, idx) => pred === actualReturns[idx]).length;
  return correctPredictions / predictions.length;
}

/**
 * Grade letter based on score
 * @param score Overall robustness score (0-1)
 * @returns Letter grade (S, A, B, C, D, E)
 */
export function gradeLetter(score: number): string {
  if (score >= 0.9) return 'S';      // Superb (90-100%)
  if (score >= 0.8) return 'A';     // Excellent (80-89%)
  if (score >= 0.7) return 'B';     // Good (70-79%)
  if (score >= 0.6) return 'C';     // Average (60-69%)
  if (score >= 0.4) return 'D';     // Below average (40-59%)
  return 'E';                       // Poor (Below 40%)
}

/**
 * Main function to calculate robustness score for backtest results
 * @param metrics Backtest metrics object
 * @returns Robustness score with detailed breakdown
 */
export function calculateRobustnessScore(metrics: BacktestMetrics): RobustnessScore {
  // Weight factors for different metrics
  const weights = {
    cagr: 0.20,           // 20% weight to CAGR
    maxDrawdown: -0.25,   // 25% negative weight to drawdown (worse = lower score)
    winRate: 0.20,        // 20% weight to win rate
    totalTrades: 0.10,    // 10% weight to trade count (for statistical significance)
    sharpeRatio: 0.15,    // 15% weight to risk-adjusted return
    hitRate: 0.10         // 10% weight to prediction accuracy
  };

  // Calculate weighted component scores (0-1 scale)
  const cagrScore = Math.min(1.0, Math.max(0.0, (metrics.cagr || 0) / 0.2)); // Normalize against 20% expected return
  const drawdownScore = 1.0 - Math.min(1.0, Math.abs(metrics.maxDrawdown || 0) / 0.4); // Inverse: lower drawdown = higher score
  const winRateScore = metrics.winRate || 0;
  const tradeCountScore = Math.min(1.0, Math.max(0.0, (metrics.totalTrades || 0) / 100)); // Normalize against 100 trades
  const sharpeScore = Math.min(1.0, Math.max(0.0, (metrics.sharpeRatio || 0) + 1)); // Normalize: -1 baseline becomes 0, 0 becomes 1, etc.
  const hitRateScore = metrics.hitRate || 0;

  // Calculate weighted score components
  const cagrWeighted = cagrScore * weights.cagr;
  const drawdownWeighted = drawdownScore * Math.abs(weights.maxDrawdown); // Use absolute value for calculation
  const winRateWeighted = winRateScore * weights.winRate;
  const tradeCountWeighted = tradeCountScore * weights.totalTrades;
  const sharpeRatioWeighted = Math.max(0, sharpeScore * weights.sharpeRatio); // Only positive contribution
  const hitRateWeighted = hitRateScore * weights.hitRate;

  // Calculate overall score (sum of positive weighted components)
  let score = cagrWeighted + drawdownWeighted + winRateWeighted + 
              tradeCountWeighted + sharpeRatioWeighted + hitRateWeighted;

  // Apply penalty for significant drawdowns
  if (metrics.maxDrawdown && metrics.maxDrawdown > 0.25) {  // >25% drawdown
    score -= 0.15; // Penalty
  }

  // Clamp score between 0 and 1
  score = Math.max(0.0, Math.min(1.0, score));

  // Calculate confidence based on data quantity and quality
  const confidence = Math.min(1.0, Math.max(0.1, 
    (metrics.totalTrades && metrics.totalTrades > 10 ? 0.7 : 0.4) + 
    (metrics.hitRate && metrics.hitRate > 0.55 ? 0.3 : 0)  // Higher hit rate = higher confidence
  ));

  return {
    score: parseFloat(score.toFixed(3)),
    grade: gradeLetter(score),
    metrics,
    breakdown: {
      cagrWeighted: parseFloat(cagrWeighted.toFixed(3)),
      drawdownWeighted: parseFloat(drawdownWeighted.toFixed(3)),
      winRateWeighted: parseFloat(winRateWeighted.toFixed(3)),
      tradeCountWeighted: parseFloat(tradeCountWeighted.toFixed(3)),
      hitRateWeighted: parseFloat(hitRateWeighted.toFixed(3))
    },
    confidence: parseFloat(confidence.toFixed(3)),
    lastUpdated: new Date().toISOString()
  };
}

/**
 * Calculate robustness scores for multiple backtest results
 * @param backtestResults Array of backtest objects with metrics
 * @returns Array of robustness scores
 */
export function calculateBatchRobustnessScores(backtestResults: any[]): RobustnessScore[] {
  return backtestResults.map(result => {
    const metrics: BacktestMetrics = {
      cagr: result.cagr || result.CAGR || result.annual_return,
      maxDrawdown: result.max_drawdown || result.maxDD || result.drawdown,
      winRate: result.win_rate || result.winRate,
      totalTrades: result.n_trades || result.total_trades || result.trade_count,
      sharpeRatio: result.sharpe_ratio || result.sharpe || result.sharpe_ratio,
      hitRate: result.hit_rate || result.accuracy || result.hit_rate
    };
    
    return calculateRobustnessScore(metrics);
  });
}

/**
 * Get a single forecast's robustness score
 * @param forecast Individual forecast object
 * @returns Robustness score for that forecast
 */
export function calculateForecastRobustness(forecast: any): RobustnessScore {
  // For individual forecasts, we consider confidence, explanation quality and consistency with other signals
  const metrics: BacktestMetrics = {
    hitRate: forecast.confidence,
    avgReturn: forecast.expected_return || forecast.expectedReturn,
    totalTrades: 1  // Single forecast
  };
  
  return calculateRobustnessScore(metrics);
}