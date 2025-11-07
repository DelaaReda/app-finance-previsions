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
      // TEMPORARY: Endpoint not yet implemented - return mock data
      // TODO: Re-enable when /api/intelligence/snapshot is ready
      // const response = await apiGet<IntelligenceSnapshot>('/api/intelligence/snapshot');
      // if (response.ok && response.data) {
      //   return response.data;
      // }

      return {
        insights: {
          summary: 'Intelligence service coming soon.',
          market_regime: {
            current: 'normal',
            explanation: 'Mock data - endpoint not yet implemented.',
          },
          opportunities: [],
          risks: [],
        },
        data_freshness: {
          forecasts_age: 'unknown',
          macro_age: 'unknown',
          news_age: 'unknown',
        },
        timestamp: new Date().toISOString(),
      } as IntelligenceSnapshot;
    },
    staleTime: 5 * 60_000, // 5 minutes
    refetchInterval: false, // Disabled while using mock data
    retry: false, // No need to retry mock data
  });
}
