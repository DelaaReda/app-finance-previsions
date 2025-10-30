// webapp/src/services/macro.service.ts
import { apiGet } from '../api/client'
import type { MacroSeries, MacroSnapshot, MacroIndicators } from '../types/macro.types'

export const macroService = {
  /**
   * Get macro time series data
   */
  getSeries: async (seriesIds?: string, limit = 200) => {
    const params: Record<string, string> = { limit: String(limit) }
    if (seriesIds) params.series_ids = seriesIds
    return apiGet<MacroSeries[]>('/macro/series', params)
  },

  /**
   * Get current macro snapshot (latest values)
   */
  getSnapshot: async () => {
    return apiGet<MacroSnapshot>('/macro/snapshot')
  },

  /**
   * Get macro indicators with trend analysis
   */
  getIndicators: async () => {
    return apiGet<MacroIndicators>('/macro/indicators')
  }
}
