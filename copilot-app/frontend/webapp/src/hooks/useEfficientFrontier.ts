/**
 * Hook for Efficient Frontier
 * Fetches efficient frontier data for portfolio optimization (EfficientFrontier widget)
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';

export interface FrontierPoint {
  risk: number; // Percentage
  return: number; // Percentage
  sharpe: number;
  weights?: Record<string, number>;
}

export interface EfficientFrontier {
  frontier: FrontierPoint[];
  tickers: string[];
  lookback_days: number;
  generated_at: string;
}

export function useEfficientFrontier() {
  return useQuery({
    queryKey: ['backtests', 'efficient_frontier'],
    queryFn: async () => {
      const response = await apiGet<any>('/api/backtests/efficient_frontier');
      
      if (response && typeof response === 'object') {
        if ('ok' in response && response.ok && 'data' in response) {
          return response.data as EfficientFrontier;
        }
        if ('data' in response) {
          return response.data as EfficientFrontier;
        }
        return response as EfficientFrontier;
      }
      
      // Fallback empty structure
      return {
        frontier: [],
        tickers: [],
        lookback_days: 252,
        generated_at: new Date().toISOString(),
      } as EfficientFrontier;
    },
    staleTime: 15 * 60 * 1000, // 15 minutes - calculs lourds mais cache agressif
    cacheTime: 30 * 60 * 1000, // 30 minutes
    retry: 2,
    retryDelay: 1000,
    refetchOnWindowFocus: false, // Éviter refetch automatique
    refetchOnMount: false, // Ne pas refetch si déjà en cache
  });
}

