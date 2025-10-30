/**
 * Service API pour le Pilier 1: MACRO
 * Gestion des données macro (FRED, VIX, GSCPI, GPR)
 */

import { apiGet } from '@/api/client'
import type { ApiResponse } from '@/types'
import type { MacroDashboard, MacroSeries, MacroIndicator } from '@/types'

export const macroService = {
  /**
   * Récupère le dashboard macro complet
   */
  getDashboard: async (): Promise<MacroDashboard> => {
    const result = await apiGet<MacroDashboard>('/macro/dashboard')
    if (!result.ok) throw new Error(result.error)
    return result.data
  },

  /**
   * Récupère une série macro spécifique
   */
  getSeries: async (seriesId: string): Promise<MacroSeries> => {
    const result = await apiGet<MacroSeries>(`/macro/series/${seriesId}`)
    if (!result.ok) throw new Error(result.error)
    return result.data
  },

  /**
   * Récupère un indicateur macro spécifique
   */
  getIndicator: async (indicatorId: string): Promise<MacroIndicator> => {
    const result = await apiGet<MacroIndicator>(`/macro/indicator/${indicatorId}`)
    if (!result.ok) throw new Error(result.error)
    return result.data
  },
}
