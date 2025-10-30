/**
 * Service API pour les Market Briefs
 * Daily/Weekly briefs avec export HTML/PDF/MD
 */

import { apiGet } from '@/api/client'
import type { 
  MarketBrief, 
  BriefFilters,
  BriefExportFormat 
} from '@/types'

export const briefService = {
  /**
   * Récupère la liste des briefs avec filtres
   */
  getBriefs: async (filters?: BriefFilters): Promise<MarketBrief[]> => {
    const params: Record<string, string> = {}
    
    if (filters?.type && filters.type !== 'all') params.type = filters.type
    if (filters?.date_from) params.date_from = filters.date_from
    if (filters?.date_to) params.date_to = filters.date_to
    if (filters?.tickers?.length) params.tickers = filters.tickers.join(',')

    const result = await apiGet<{ briefs: MarketBrief[] }>('/briefs', params)
    if (!result.ok) throw new Error(result.error)
    return result.data.briefs
  },

  /**
   * Récupère un brief spécifique
   */
  getBrief: async (id: string): Promise<MarketBrief> => {
    const result = await apiGet<MarketBrief>(`/briefs/${id}`)
    if (!result.ok) throw new Error(result.error)
    return result.data
  },

  /**
   * Génère le brief le plus récent
   */
  getLatest: async (type: 'daily' | 'weekly' = 'daily'): Promise<MarketBrief> => {
    const result = await apiGet<MarketBrief>('/briefs/latest', { type })
    if (!result.ok) throw new Error(result.error)
    return result.data
  },
}
