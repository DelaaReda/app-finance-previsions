import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { api } from '@/api/client';
import { qk } from '@/lib/keys';

/**
 * Ticker search result
 */
export interface TickerSearchResult {
  ticker: string;
  name: string;
  sector: string;
  match_type: 'symbol' | 'name' | 'sector';
}

/**
 * Ticker search response
 */
export interface TickerSearchResponse {
  query: string;
  matches: TickerSearchResult[];
  total: number;
  has_more: boolean;
}

/**
 * Search tickers by query
 * 
 * @param query - Search query (ticker symbol or company name)
 * @param limit - Maximum number of results (default: 10)
 * @param sector - Optional sector filter
 * @param enabled - Whether to enable the query (default: true when query length > 0)
 */
export function useSearchTickers(
  query: string,
  limit: number = 10,
  sector?: string,
  enabled?: boolean
): UseQueryResult<TickerSearchResponse> {
  // Only enable if query has content
  const shouldEnable = enabled !== undefined ? enabled : query.trim().length > 0;

  return useQuery<TickerSearchResponse>({
    queryKey: qk.search('tickers', query, limit, sector),
    enabled: shouldEnable,
    staleTime: 5 * 60_000, // 5 minutes (ticker list doesn't change often)
    gcTime: 10 * 60_000, // 10 minutes
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('q', query);
      params.append('limit', String(limit));
      if (sector) {
        params.append('sector', sector);
      }

      const data = await api.fetchJson<any>('/search/tickers', {
        searchParams: params,
      });

      // Extract from API response envelope
      if (data && data.ok && data.data) {
        return data.data;
      }

      // Fallback
      return {
        query,
        matches: [],
        total: 0,
        has_more: false,
      };
    },
  });
}

/**
 * Get list of available sectors
 */
export function useSectors(): UseQueryResult<string[]> {
  return useQuery<string[]>({
    queryKey: qk.search('sectors'),
    staleTime: 60 * 60_000, // 1 hour (sectors don't change)
    gcTime: 2 * 60 * 60_000, // 2 hours
    queryFn: async () => {
      const data = await api.fetchJson<any>('/search/sectors');

      // Extract from API response envelope
      if (data && data.ok && data.data && data.data.sectors) {
        return data.data.sectors;
      }

      // Fallback
      return [];
    },
  });
}
