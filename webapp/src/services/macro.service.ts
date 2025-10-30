// Service pour les données macro (Pilier 1)
import { apiGet } from '../api/client'
import type { ApiResponse } from '../types/common'
import type { MacroSeriesResponse } from '../types/macro'

export async function fetchMacroSeries(
  ids: string[],
  start?: string,
  end?: string
): Promise<ApiResponse<MacroSeriesResponse>> {
  const params: Record<string, string> = {}
  
  // Note: apiGet n'accepte pas les tableaux directement, on passe des params multiples
  // Pour l'instant, on va construire la query string manuellement
  const query = ids.map(id => `ids=${encodeURIComponent(id)}`).join('&')
  const fullPath = `/macro/series?${query}${start ? `&start=${start}` : ''}${end ? `&end=${end}` : ''}`
  
  return apiGet<MacroSeriesResponse>(fullPath.replace('/macro', ''))
}

export async function fetchMacroBundle(): Promise<ApiResponse<any>> {
  return apiGet<any>('/macro/bundle')
}
