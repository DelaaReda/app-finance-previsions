import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';

/**
 * Market Context (Regime) types
 */
export type MarketRegime =
  | 'HIGH_VOLATILITY'
  | 'ELEVATED_RISK'
  | 'BULL_MARKET'
  | 'BEAR_MARKET'
  | 'RISK_OFF'
  | 'RISK_ON'
  | 'NORMAL';

/**
 * Market Context Response Structure
 */
export interface MarketContext {
  regime: MarketRegime;
  confidence: number;
  key_drivers: string[];
  characteristics: {
    volatility: 'low' | 'medium' | 'high' | 'extreme';
    sentiment: 'bullish' | 'bearish' | 'neutral';
    trend: 'up' | 'down' | 'sideways';
    momentum?: 'strong' | 'moderate' | 'weak';
    risk_level: 'low' | 'medium' | 'high';
  };
  recommended_layout: {
    primary_widgets: string[];
    secondary_widgets?: string[];
    filters?: Record<string, any>;
    emphasis?: string;
  };
  timestamp: string;
}

/**
 * Hook to fetch Market Context data
 * 
 * @returns React Query result with Market Context
 * 
 * Features:
 * - Auto-refetch every 5 minutes
 * - Stale time 5 minutes
 * - Error handling with fallback
 * 
 * Usage:
 * ```tsx
 * const { data: context, isLoading, error } = useMarketContext();
 * ```
 */
export function useMarketContext() {
  return useQuery<MarketContext>({
    queryKey: ['context', 'current'],
    queryFn: async () => {
      // TEMPORARY: Endpoint not yet implemented - return mock data
      // TODO: Re-enable when /api/context/current is ready
      // const response = await apiGet<MarketContext>('/api/context/current');
      // if (response.ok && response.data) {
      //   return response.data;
      // }

      return {
        regime: 'NORMAL',
        confidence: 0,
        key_drivers: [],
        characteristics: {
          volatility: 'medium',
          sentiment: 'neutral',
          trend: 'sideways',
          risk_level: 'medium',
        },
        recommended_layout: {
          primary_widgets: [],
        },
        timestamp: new Date().toISOString(),
      } satisfies MarketContext;
    },
    staleTime: 5 * 60_000, // 5 minutes
    refetchInterval: false, // Disabled while using mock data
    retry: false, // No need to retry mock data
  });
}
