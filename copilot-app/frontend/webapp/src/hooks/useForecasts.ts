/**
 * Enhanced forecasts hook with filtering capabilities
 * Matches the enhanced FC-P0-004 backend API with filtering, confidence thresholds, and hybrid ML+G4F features
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';
import { ensureArray } from '@/lib/safe';

export function useForecasts(filters: {
  tickers?: string[],
  horizon?: string,
  themes?: string[],
  limit?: number,
  sort_by?: string,
  min_confidence?: number
} = {}) {
  return useQuery({
    queryKey: ['forecasts', filters],
    queryFn: async () => {
      // Build query parameters
      const params: Record<string, any> = {};
      
      if (filters.tickers && filters.tickers.length > 0) {
        params.tickers = filters.tickers.join(',');
      }
      
      if (filters.horizon) {
        params.horizon = filters.horizon;
      }
      
      if (filters.themes && filters.themes.length > 0) {
        params.themes = filters.themes.join(',');
      }
      
      if (filters.limit) {
        params.limit = filters.limit;
      }
      
      if (filters.sort_by) {
        params.sort_by = filters.sort_by;
      }
      
      if (filters.min_confidence !== undefined) {
        params.min_confidence = filters.min_confidence;
      }
      
      const response = await apiGet<any>('/api/forecasts', params);
      
      // Handle the response according to the backend's {ok, data} format
      if (response.ok && response.data) {
        // If the data has rows field, return it (standard format)
        if (response.data.rows !== undefined) {
          return {
            rows: ensureArray(response.data.rows),
            freshness: response.data.freshness || response.data.last_update,
            source: response.data.source || [],
            generated_at: response.data.generated_at,
            count: response.data.count || ensureArray(response.data.rows).length
          };
        } 
        // If the data has items field, return it (alternative format)
        else if (response.data.items !== undefined) {
          return {
            rows: ensureArray(response.data.items),
            freshness: response.data.freshness || response.data.last_update,
            source: response.data.source || [],
            generated_at: response.data.generated_at,
            count: response.data.count || ensureArray(response.data.items).length
          };
        }
        // If data is just an array, return it as rows
        else if (Array.isArray(response.data)) {
          return {
            rows: ensureArray(response.data),
            freshness: response.freshness || response.last_update,
            source: response.source || [],
            generated_at: response.generated_at,
            count: response.data.length
          };
        }
        // Otherwise, return the data as is but ensure it's structured properly
        else {
          return {
            rows: ensureArray(response.data),
            freshness: response.freshness || response.last_update,
            source: response.source || [],
            generated_at: response.generated_at,
            count: 0
          };
        }
      } else if (response.ok) {
        // If response.ok is true but no data, return empty structure
        return {
          rows: [],
          count: 0,
          error: response.error || "No data returned from server"
        };
      } else {
        // If response.ok is false, return empty with error
        throw new Error(response.error || "Failed to fetch forecasts");
      }
    },
    staleTime: 300000, // 5 minutes
    cacheTime: 600000, // 10 minutes
    retry: 2,
    retryDelay: 1000,
  });
}