// Service pour le brief et dashboard
import { apiGet } from '../api/client'
import type { ApiResponse } from '../types/common'
import type { BriefData } from '../types/brief'
import type { BriefFilters, MarketBrief } from '../types/brief.types'

export const briefService = {
  /**
   * Get list of briefs
   */
  getBriefs: async (filters?: BriefFilters): Promise<ApiResponse<MarketBrief[]>> => {
    // For now, return a mock response or query the brief endpoint
    return apiGet<MarketBrief[]>('/brief', filters);
  },

  /**
   * Get specific brief by ID
   */
  getBrief: async (id: string): Promise<ApiResponse<MarketBrief>> => {
    return apiGet<MarketBrief>(`/brief/${id}`);
  },

  /**
   * Get latest brief of specified type
   */
  getLatest: async (type: 'daily' | 'weekly' = 'daily', universe: string[] = ['SPY', 'QQQ']): Promise<ApiResponse<MarketBrief>> => {
    // Use query parameters for period and universe
    const params: Record<string, any> = {
      period: type,
      universe: universe
    };
    return apiGet<MarketBrief>('/brief', params);
  }
};

// Update the BriefData interface to match backend response
export interface BriefData {
  top_signals: any[];
  top_risks: any[];
  picks: any[];
  sources: any[];
  generated_at: string;
  period: string;
  universe: string[];
}

// Export function for backward compatibility
export async function fetchBrief(
  period: 'daily' | 'weekly' = 'weekly',
  universe: string[] = ['SPY', 'QQQ']
): Promise<ApiResponse<BriefData>> {
  // Use the correct endpoint with query parameters
  const params: Record<string, any> = {
    period: period,
    universe: universe
  };
  
  return apiGet<BriefData>('/brief', params);
}
