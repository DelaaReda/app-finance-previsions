// Service pour le brief et dashboard
import { apiGet } from '../api/client'
import type { ApiResponse } from '../types/common'
import type { MarketBrief } from '../types/brief.types'

export const briefService = {
  /**
   * Get list of briefs
   * NOTE: Backend doesn't currently support listing multiple briefs, only latest daily/weekly
   * For now, return empty array or a mock response
   */
  getBriefs: async (_filters?: Record<string, any>): Promise<ApiResponse<MarketBrief[]>> => {
    // Backend doesn't currently support a list endpoint, so return empty array
    // Could implement this later with actual backend support
    return { ok: true, data: [] }
  },

  /**
   * Get specific brief by ID
   */
  getBrief: async (id: string): Promise<ApiResponse<MarketBrief>> => {
    return apiGet<MarketBrief>(`/api/brief/${id}`);
  },

  /**
   * Get latest brief of specified type
   */
  getLatest: async (type: 'daily' | 'weekly' = 'daily', _universe: string[] = ['SPY', 'QQQ']): Promise<ApiResponse<MarketBrief>> => {
    // Use the correct endpoint for daily or weekly briefs
    const endpoint = type === 'daily' ? '/api/brief/daily' : '/api/brief/weekly'
    // Note: universe filters are not currently supported in backend endpoints
    // This would require backend changes to support universe filtering
    
    const response = await apiGet(endpoint, {});
    
    // Handle different response formats - some endpoints return nested data while others return direct
    if (response.ok && response.data) {
      // Check if the response follows { ok, data } format with nested content
      if (response.data.data) {
        // If response is { ok: true, data: { data: { ... }, ... } }
        return {
          ok: true,
          data: response.data.data
        };
      } else {
        // Direct format: { ok: true, data: { ... } }
        return response;
      }
    }
    
    return response;
  }
}

// Export function for backward compatibility
export async function fetchBrief(
  period: 'daily' | 'weekly' = 'weekly',
  _universe: string[] = ['SPY', 'QQQ']
): Promise<ApiResponse<MarketBrief>> {
  // Use the correct endpoint for daily or weekly briefs
  const endpoint = period === 'daily' ? '/api/brief/daily' : '/api/brief/weekly'
  
  return apiGet<MarketBrief>(endpoint, {});
}
