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
  const isDev = import.meta.env.DEV;
  
  if (isDev) {
    console.log(`[Hook] 🧠 useIntelligence called`);
  }
  
  return useQuery<IntelligenceSnapshot>({
    queryKey: ['intelligence', 'snapshot'],
    queryFn: async () => {
      if (isDev) {
        console.log(`[Hook] 🔄 useIntelligence - Fetching snapshot...`);
      }
      
      const startTime = performance.now();
      const response = await apiGet<IntelligenceSnapshot>('/api/intelligence/snapshot');
      const elapsed = performance.now() - startTime;
      
      if (isDev) {
        console.log(`[Hook] ⏱️ useIntelligence - Response received in ${elapsed.toFixed(0)}ms`, {
          ok: response.ok,
          hasData: !!response.data
        });
      }
      
      if (!response.ok || !response.data) {
        if (isDev) {
          console.error(`[Hook] ❌ useIntelligence - Failed`, { error: response.error });
        }
        throw new Error(response.error ?? 'Unable to load intelligence snapshot');
      }
      
      if (isDev) {
        const insights = response.data.insights;
        console.log(`[Hook] ✅ useIntelligence - Success`, {
          regime: insights.market_regime?.current,
          opportunitiesCount: insights.opportunities?.length || 0,
          risksCount: insights.risks?.length || 0,
          summary: insights.summary?.substring(0, 100)
        });
      }
      
      return response.data;
    },
    staleTime: 5 * 60_000, // 5 minutes
    refetchInterval: 5 * 60_000,
    retry: 1,
  });
}
