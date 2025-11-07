/**
 * Backtest Service - API Client
 * Task: FC-P0-004 - Cache persistant générique + FC-P1-015 - Backtests v1
 */

import { apiGet } from '@/api/client';
import type { ApiResponse } from '@/types/common.types';

export interface BacktestResult {
  ticker: string;
  period: string;
  hit_rate: number;
  avg_return: number;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  n_trades: number;
  confidence: number;
  explanation?: string;
}

export interface BacktestMetrics {
  results: BacktestResult[];
  overall_metrics: {
    hit_rate: number;
    avg_return: number;
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    n_trades: number;
  };
  params_used: {
    start_date: string;
    end_date: string;
    universe: string[];
    strategy: string;
  };
  freshness: string;
  source: string[];
}

class BacktestService {
  async getBacktests(
    params: {
      start?: string;
      end?: string;
      universe?: string[];
      strategy?: string;
      horizon?: string;
    } = {}
  ): Promise<ApiResponse<BacktestMetrics>> {
    try {
      // Construct query parameters
      const queryParams: Record<string, string | number | boolean> = {};
      
      if (params.start) queryParams.start = params.start;
      if (params.end) queryParams.end = params.end;
      if (params.universe) queryParams.universe = params.universe.join(',');
      if (params.strategy) queryParams.strategy = params.strategy;
      if (params.horizon) queryParams.horizon = params.horizon;

      // Use the apiGet function that already handles the {ok, data} envelope
      const response = await apiGet<ApiResponse<BacktestMetrics>>('/backtests', queryParams);
      
      return response;
    } catch (error) {
      console.error('Error fetching backtests:', error);
      
      // Return a structured fallback response to prevent crashes
      return {
        ok: false,
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch backtests'
      };
    }
  }

  async getBacktestForTicker(
    ticker: string,
    params: {
      start?: string;
      end?: string;
      strategy?: string;
      horizon?: string;
    } = {}
  ): Promise<ApiResponse<BacktestResult[]>> {
    try {
      const queryParams: Record<string, string | number | boolean> = { ticker };
      
      if (params.start) queryParams.start = params.start;
      if (params.end) queryParams.end = params.end;
      if (params.strategy) queryParams.strategy = params.strategy;
      if (params.horizon) queryParams.horizon = params.horizon;

      // Use the apiGet function that already handles the {ok, data} envelope
      const response = await apiGet<ApiResponse<BacktestResult[]>>(
        `/backtests/detail/${ticker}`, 
        queryParams
      );

      return response;
    } catch (error) {
      console.error(`Error fetching backtest for ${ticker}:`, error);
      
      // Return a structured fallback response
      return {
        ok: false,
        data: null,
        error: error instanceof Error ? error.message : `Failed to fetch backtest for ${ticker}`
      };
    }
  }

  async getBacktestMetrics(): Promise<ApiResponse<any>> {
    try {
      // Use the apiGet function that already handles the {ok, data} envelope
      const response = await apiGet<ApiResponse<any>>('/backtests/metrics');
      
      return response;
    } catch (error) {
      console.error('Error fetching backtest metrics:', error);
      
      return {
        ok: false,
        data: null,
        error: error instanceof Error ? error.message : 'Failed to fetch backtest metrics'
      };
    }
  }
}

export const backtestService = new BacktestService();

export default backtestService;