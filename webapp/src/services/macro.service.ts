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

/**
 * Fetch macro series data (alias for use in components)
 */
export const fetchMacroSeries = async (seriesIds: string[], start?: string) => {
  const seriesIdsParam = seriesIds.join(',')
  const params: Record<string, string> = { series_ids: seriesIdsParam }
  if (start) params.start = start
  return macroService.getSeries(seriesIdsParam)
}
