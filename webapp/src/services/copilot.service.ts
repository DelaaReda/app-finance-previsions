// Service pour le pilier Copilot (LLM + RAG)

import { apiGet, apiPost } from './api'
import { 
  CopilotSession, 
  CopilotQuery, 
  CopilotResponse, 
  WhatIfScenario,
  RAGContext 
} from '@/types/copilot.types'
import type { ApiResult } from './api'

export const copilotService = {
  // Créer une nouvelle session
  createSession: async (context?: RAGContext): Promise<ApiResult<CopilotSession>> => {
    return apiPost<CopilotSession>('/copilot/session', { context })
  },

  // Obtenir une session
  getSession: async (sessionId: string): Promise<ApiResult<CopilotSession>> => {
    return apiGet<CopilotSession>(`/copilot/session/${sessionId}`)
  },

  // Poser une question
  ask: async (
    sessionId: string, 
    query: CopilotQuery
  ): Promise<ApiResult<CopilotResponse>> => {
    return apiPost<CopilotResponse>(`/copilot/session/${sessionId}/ask`, query)
  },

  // Question rapide sans session
  quickAsk: async (query: CopilotQuery): Promise<ApiResult<CopilotResponse>> => {
    return apiPost<CopilotResponse>('/copilot/ask', query)
  },
  // Scénarios what-if
  getScenarios: async (): Promise<ApiResult<WhatIfScenario[]>> => {
    return apiGet<WhatIfScenario[]>('/copilot/scenarios')
  },

  createScenario: async (scenario: Omit<WhatIfScenario, 'id' | 'createdAt'>): Promise<ApiResult<WhatIfScenario>> => {
    return apiPost<WhatIfScenario>('/copilot/scenarios', scenario)
  },

  runScenario: async (scenarioId: string): Promise<ApiResult<any>> => {
    return apiPost(`/copilot/scenarios/${scenarioId}/run`, {})
  },

  // Stats RAG
  getRAGStats: async (): Promise<ApiResult<{
    documentsIndexed: number
    timeRange: { start: string; end: string }
    lastUpdate: string
    coverage: { news: number; macro: number; prices: number }
  }>> => {
    return apiGet('/copilot/rag/stats')
  }
}
