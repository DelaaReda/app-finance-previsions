/**
 * Service API pour le Pilier 2: ACTIONS
 * Gestion des actions, indicateurs techniques, secteurs
 */

import { apiGet } from '@/api/client'
import type { 
  StockAnalysis, 
  TechnicalIndicators,
  SectorComparison,
  TickerSheet 
} from '@/types'

export const stocksService = {
  /**
   * Récupère l'analyse complète d'une action
   */
  getStockAnalysis: async (ticker: string): Promise<StockAnalysis> => {
    const result = await apiGet<StockAnalysis>(`/stocks/${ticker}/analysis`)
    if (!result.ok) throw new Error(result.error)
    return result.data
  },

  /**
   * Récupère les indicateurs techniques d'une action
   */
  getTechnicalIndicators: async (ticker: string): Promise<TechnicalIndicators> => {
    const result = await apiGet<TechnicalIndicators>(`/stocks/${ticker}/technical`)
    if (!result.ok) throw new Error(result.error)
    return result.data
  },
}
