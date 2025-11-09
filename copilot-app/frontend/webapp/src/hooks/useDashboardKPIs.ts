/**
 * Hook for Dashboard KPIs
 * Fetches aggregated KPIs for dashboard widgets (MetricCard, StatsGrid)
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';

export interface DashboardKPIs {
  // KPIs basiques
  last_forecast_dt?: string | null;
  total_forecasts?: number;
  tickers_tracked?: number;
  available_horizons?: string[];
  
  // Top signaux et risques (nouveau)
  top_signals?: Array<{
    ticker: string;
    direction?: string;
    confidence?: number;
    expected_return?: number;
    horizon?: string;
    reason?: string;
    composite_score?: number;
    macro_score?: number;
    technical_score?: number;
    news_score?: number;
  }>;
  top_risks?: Array<{
    ticker: string;
    direction?: string;
    confidence?: number;
    expected_return?: number;
    horizon?: string;
    reason?: string;
    composite_score?: number;
    macro_score?: number;
    technical_score?: number;
    news_score?: number;
  }>;
  
  // Structure legacy (pour compatibilité)
  forecasts?: {
    total: number;
    high_confidence: number;
    avg_confidence: number;
    bullish: number;
    bearish: number;
  };
  backtests?: {
    hit_rate: number;
    sharpe_ratio: number;
    status: string;
  };
  news?: {
    recent_count: number;
    avg_score: number;
  };
  system?: {
    last_forecast_update?: string;
    last_news_update?: string;
    last_backtest_update?: string;
  };
  generated_at: string;
}

export function useDashboardKPIs() {
  return useQuery({
    queryKey: ['dashboard', 'kpis'],
    queryFn: async () => {
      const response = await apiGet<any>('/api/dashboard/kpis');
      
      // Handle the response according to the backend's {ok, data} format
      if (response && typeof response === 'object') {
        if ('ok' in response && response.ok && 'data' in response) {
          return response.data as DashboardKPIs;
        }
        if ('data' in response) {
          return response.data as DashboardKPIs;
        }
        // Direct data response
        return response as DashboardKPIs;
      }
      
      // Fallback empty structure
      return {
        forecasts: {
          total: 0,
          high_confidence: 0,
          avg_confidence: 0,
          bullish: 0,
          bearish: 0,
        },
        backtests: {
          hit_rate: 0,
          sharpe_ratio: 0,
          status: 'pending',
        },
        news: {
          recent_count: 0,
          avg_score: 0,
        },
        system: {},
        generated_at: new Date().toISOString(),
      } as DashboardKPIs;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes - données KPIs changent souvent
    cacheTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
    retryDelay: 1000,
    refetchOnWindowFocus: false, // Éviter refetch automatique
    refetchOnMount: true, // Refetch au montage pour données fraîches
  });
}

