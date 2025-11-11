import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';

/**
 * Recommendation from backend
 */
export interface Recommendation {
  ticker: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  score: number;
  reasoning: string;
  catalysts: string[];
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  confidence: number;
  supporting_data?: {
    forecast_confidence?: number;
    news_sentiment?: number;
    momentum_score?: number;
    macro_alignment?: number;
  };
}

export interface RecommendationsResponse {
  recommendations: Recommendation[];
  market_context: {
    regime: string;
    summary: string;
    key_drivers: string[];
  };
  generated_at: string;
  valid_until: string;
}

/**
 * Hook to fetch daily recommendations
 * 
 * @param universe - Optional list of tickers
 * @param limit - Number of recommendations (default 3)
 */
export function useRecommendations(universe?: string[], limit: number = 3) {
  const isDev = import.meta.env.DEV;
  
  if (isDev) {
    console.log(`[Hook] 🎯 useRecommendations called`, { universe, limit });
  }
  
  return useQuery<RecommendationsResponse>({
    queryKey: ['recommendations', 'daily', universe, limit],
    queryFn: async () => {
      if (isDev) {
        console.log(`[Hook] 🔄 useRecommendations - Fetching data...`, { universe, limit });
      }
      
      // Build query parameters
      const params = new URLSearchParams();
      if (universe && universe.length > 0) {
        universe.forEach(ticker => params.append('universe', ticker));
      }
      params.append('limit', limit.toString());

      const startTime = performance.now();
      const response = await apiGet<RecommendationsResponse>(
        `/api/recommendations/daily?${params.toString()}`
      );
      const elapsed = performance.now() - startTime;
      
      if (isDev) {
        console.log(`[Hook] ⏱️ useRecommendations - Response received in ${elapsed.toFixed(0)}ms`, {
          ok: response.ok,
          hasData: !!response.data,
          recommendationsCount: response.data?.recommendations?.length || 0
        });
      }
      
      if (response.ok && response.data) {
        if (isDev) {
          console.log(`[Hook] ✅ useRecommendations - Success`, {
            recommendations: response.data.recommendations.map(r => ({
              ticker: r.ticker,
              action: r.action,
              score: r.score
            })),
            regime: response.data.market_context?.regime
          });
        }
        return response.data;
      }
      
      if (isDev) {
        console.warn(`[Hook] ⚠️ useRecommendations - Using fallback`, { error: response.error });
      }

      // Fallback if endpoint returns empty or error
      return {
        recommendations: [],
        market_context: {
          regime: 'NORMAL',
          summary: 'Recommendations service is analyzing market conditions.',
          key_drivers: [],
        },
        generated_at: new Date().toISOString(),
        valid_until: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // 24h from now
      } satisfies RecommendationsResponse;
    },
    staleTime: 60 * 60_000, // 1 hour (recommendations are daily)
    refetchInterval: 60 * 60_000, // Refetch every hour
    retry: 1,
  });
}
