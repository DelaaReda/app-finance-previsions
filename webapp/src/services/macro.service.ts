// Service pour le pilier Macro

import { apiGet } from './api'
import { MacroDashboard, MacroIndicator, MacroSeries } from '@/types/macro.types'
import type { ApiResult } from './api'

export const macroService = {
  // Dashboard macro complet
  getDashboard: async (): Promise<ApiResult<MacroDashboard>> => {
    return apiGet<MacroDashboard>('/macro/dashboard')
  },

  // Liste des indicateurs macro
  getIndicators: async (category?: string): Promise<ApiResult<MacroIndicator[]>> => {
    return apiGet<MacroIndicator[]>('/macro/indicators', category ? { category } : undefined)
  },

  // Série temporelle d'un indicateur
  getSeries: async (
    symbol: string, 
    startDate?: string, 
    endDate?: string
  ): Promise<ApiResult<MacroSeries>> => {
    const params: Record<string, string> = { symbol }
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    return apiGet<MacroSeries>('/macro/series', params)
  },

  // Régime macro actuel
  getRegime: async (): Promise<ApiResult<{ current: string; confidence: number; changeDate: string }>> => {
    return apiGet('/macro/regime')
  }
}
