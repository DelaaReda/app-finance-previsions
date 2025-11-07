/**
 * Backtest hooks for React Query - Finance Copilot
 * Task: FC-P0-004 - Cache persistant + FC-P1-015 - Backtests v1
 */

import { useQuery } from '@tanstack/react-query';
import { backtestService, type BacktestMetrics, type BacktestResult } from '@/services/backtest.service';

export function useBacktests(
  params: {
    start?: string;
    end?: string;
    universe?: string[];
    strategy?: string;
    horizon?: string;
  } = {}
) {
  return useQuery({
    queryKey: ['backtests', params],
    queryFn: async () => {
      const result = await backtestService.getBacktests(params);
      
      // Properly handle the response following the {ok, data, error} pattern
      if (!result.ok || !result.data) {
        // Return structured fallback if backend is unavailable
        return {
          results: [],
          overall_metrics: {
            hit_rate: 0.0,
            avg_return: 0.0,
            total_return: 0.0,
            sharpe_ratio: 0.0,
            max_drawdown: 0.0,
            n_trades: 0
          },
          params_used: {
            start_date: "unknown",
            end_date: "unknown",
            universe: params.universe || [],
            strategy: params.strategy || "default"
          },
          freshness: "unknown",
          source: ["fallback_empty"],
          error: result.error
        };
      }
      
      return result.data;
    },
    staleTime: 300000, // 5 minutes
    cacheTime: 600000, // 10 minutes
    retry: 2,
    retryDelay: 1000,
  });
}

export function useBacktestForTicker(
  ticker: string,
  params: {
    start?: string;
    end?: string;
    strategy?: string;
    horizon?: string;
  } = {}
) {
  return useQuery({
    queryKey: ['backtests', 'ticker', ticker, params],
    queryFn: async () => {
      const result = await backtestService.getBacktestForTicker(ticker, params);
      
      if (!result.ok || !result.data) {
        // Return structured fallback if backend is unavailable
        return [];
      }
      
      return result.data;
    },
    staleTime: 300000, // 5 minutes
    cacheTime: 600000, // 10 minutes
    retry: 2,
    retryDelay: 1000,
    enabled: !!ticker, // Only run query if ticker is provided
  });
}

export function useBacktestMetrics() {
  return useQuery({
    queryKey: ['backtests', 'metrics'],
    queryFn: async () => {
      const result = await backtestService.getBacktestMetrics();
      
      if (!result.ok || !result.data) {
        // Return structured fallback if backend is unavailable
        return {
          overall_hit_rate: 0.0,
          avg_expected_return: 0.0,
          total_trades_evaluated: 0,
          accuracy_trend: "unknown",
          avg_confidence: 0.0,
          last_update: null,
          model_performance: {
            precision: 0.0,
            recall: 0.0,
            f1_score: 0.0
          }
        };
      }
      
      return result.data;
    },
    staleTime: 300000, // 5 minutes
    cacheTime: 600000, // 10 minutes
    retry: 2,
    retryDelay: 1000,
  });
}

// Type definitions for the backtest API responses
export type { BacktestMetrics, BacktestResult };