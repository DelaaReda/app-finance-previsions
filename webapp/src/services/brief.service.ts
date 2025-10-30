// Service pour le brief et dashboard
import { apiGet } from '../api/client'
import type { ApiResponse } from '../types/common'
import type { BriefData } from '../types/brief'

export async function fetchBrief(
  period: 'daily' | 'weekly' = 'weekly',
  universe: string[] = ['SPY', 'QQQ']
): Promise<ApiResponse<BriefData>> {
  const universeQuery = universe.map(u => `universe=${encodeURIComponent(u)}`).join('&')
  return apiGet<BriefData>(`/brief?period=${period}&${universeQuery}`)
}
