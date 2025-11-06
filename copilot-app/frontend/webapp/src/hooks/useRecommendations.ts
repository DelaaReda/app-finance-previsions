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
  return useQuery<RecommendationsResponse>({
    queryKey: ['recommendations', 'daily', universe, limit],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (universe) {
        universe.forEach(ticker => params.append('universe', ticker));
      }
      params.append('limit', limit.toString());
      
      const response = await apiGet<RecommendationsResponse>(
        `/recommendations/daily?${params.toString()}`
      );
      return response.data;
    },
    staleTime: 60 * 60_000, // 1 hour (recommendations are daily)
    refetchInterval: 60 * 60_000, // Auto-refetch every hour
    retry: 2,
  });
}
