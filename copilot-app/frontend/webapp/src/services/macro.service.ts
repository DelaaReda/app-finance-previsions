// webapp/src/services/macro.service.ts
import { apiGet } from '../api/client'
import type { MacroSeries, MacroSnapshot, MacroIndicators } from '../types/macro.types'

export const macroService = {
  /**
   * Get macro time series data
   */
  getSeries: async (seriesIds?: string, limit = 200, format?: 'array' | 'map') => {
    const params: Record<string, string> = { limit: String(limit) }
    if (seriesIds) params.series_ids = seriesIds
    if (format) params.format_resp = format  // Use format_resp parameter for map response
    return apiGet<MacroSeries[]>('/api/macro/series', params)
  },

  /**
   * Get current macro snapshot (latest values)
   */
  getSnapshot: async () => {
    return apiGet<MacroSnapshot>('/api/macro/snapshot')
  },

  /**
   * Get macro indicators with trend analysis
   */
  getIndicators: async () => {
    return apiGet<MacroIndicators>('/api/macro/indicators')
  }
}

/**
 * Fetch macro series data (alias for use in components)
 */
export const fetchMacroSeries = async (seriesIds: string[], start?: string, format?: 'array' | 'map') => {
  const seriesIdsParam = seriesIds.join(',')
  return macroService.getSeries(seriesIdsParam, 200, format)
}
