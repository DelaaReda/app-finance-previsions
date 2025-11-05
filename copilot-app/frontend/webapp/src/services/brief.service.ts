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
    return apiGet<MarketBrief>(`/brief/${id}`);
  },

  /**
   * Get latest brief of specified type
   */
  getLatest: async (type: 'daily' | 'weekly' = 'daily', _universe: string[] = ['SPY', 'QQQ']): Promise<ApiResponse<MarketBrief>> => {
    // Use the correct endpoint for daily or weekly briefs
    const endpoint = type === 'daily' ? '/brief/daily' : '/brief/weekly'
    // Note: universe filters are not currently supported in backend endpoints
    // This would require backend changes to support universe filtering
    
    return apiGet<MarketBrief>(endpoint, {});
  }
}

// Export function for backward compatibility
export async function fetchBrief(
  period: 'daily' | 'weekly' = 'weekly',
  _universe: string[] = ['SPY', 'QQQ']
): Promise<ApiResponse<MarketBrief>> {
  // Use the correct endpoint for daily or weekly briefs
  const endpoint = period === 'daily' ? '/brief/daily' : '/brief/weekly'
  
  return apiGet<MarketBrief>(endpoint, {});
}
