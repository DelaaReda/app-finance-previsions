import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';

/**
 * Intelligence Service Response Structure
 */
export interface IntelligenceSnapshot {
  insights: {
    summary: string;
    market_regime: {
      current: string;
      explanation: string;
    };
    opportunities: Array<{
      ticker: string;
      reasoning: string;
      confidence: number;
    }>;
    risks: Array<{
      type: string;
      description: string;
      severity: 'HIGH' | 'MEDIUM' | 'LOW';
    }>;
  };
  data_freshness: {
    forecasts_age: string;
    macro_age: string;
    news_age: string;
  };
  timestamp: string;
}

/**
 * Hook to fetch Intelligence Service data
 * 
 * @returns React Query result with Intelligence Snapshot
 * 
 * Features:
 * - Auto-refetch every 5 minutes
 * - Stale time 5 minutes
 * - Error handling with fallback
 * 
 * Usage:
 * ```tsx
 * const { data, isLoading, error } = useIntelligence();
 * ```
 */
export function useIntelligence() {
  return useQuery<IntelligenceSnapshot>({
    queryKey: ['intelligence', 'snapshot'],
    queryFn: async () => {
      const response = await apiGet<IntelligenceSnapshot>('/api/intelligence/snapshot');
      return response.data;
    },
    staleTime: 5 * 60_000, // 5 minutes
    refetchInterval: 5 * 60_000, // Auto-refetch every 5 minutes
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });
}
