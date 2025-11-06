/**
 * useCorrelationIntelligence Hook
 * 
 * Fetches correlation intelligence data from the backend.
 * Provides correlation matrix, interesting pairs, and LLM explanations.
 * 
 * Author: ELENA-39
 * Task: FC-INT-025
 */

import { useQuery } from '@tanstack/react-query';

export interface CorrelationPair {
  ticker1: string;
  ticker2: string;
  correlation: number;
  strength: 'strong' | 'moderate';
  direction: 'positive' | 'negative';
  explanation: string;
  drivers: string[];
  implications: string[];
  action_type: 'HEDGE' | 'DIVERSIFY' | 'ARBITRAGE' | 'MONITOR';
  action_description: string;
}

export interface CorrelationIntelligence {
  matrix: number[][];
  tickers: string[];
  interesting_pairs: CorrelationPair[];
  summary: string;
  market_context: {
    regime: string;
    characteristics?: Record<string, any>;
  };
  generated_at: string;
  valid_until: string;
  error?: string;
}

export interface UseCorrelationIntelligenceOptions {
  universe?: string[];
  window?: string;
  threshold?: number;
}

export function useCorrelationIntelligence(options: UseCorrelationIntelligenceOptions = {}) {
  const { universe, window = '30d', threshold = 0.7 } = options;

  return useQuery<CorrelationIntelligence>({
    queryKey: ['correlations', 'analyzed', universe, window, threshold],
    queryFn: async () => {
      // Build URL with query params
      const params = new URLSearchParams();
      if (universe && universe.length > 0) {
        universe.forEach(ticker => params.append('universe', ticker));
      }
      params.append('window', window);
      params.append('threshold', threshold.toString());

      const url = `/api/correlations/analyzed?${params.toString()}`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to fetch correlation intelligence: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    },
    staleTime: 60 * 60_000, // 1 hour - correlations don't change frequently
    refetchInterval: 60 * 60_000, // Auto-refetch every hour
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });
}
