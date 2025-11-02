// webapp/src/services/copilot.service.ts
import { apiGet, apiPost } from '../api/client'
import type { CopilotAskRequest, CopilotResponse, CopilotHistory } from '../types/copilot.types'

export const copilotService = {
  /**
   * Ask LLM with RAG (5 years context)
   */
  ask: async (request: CopilotAskRequest) => {
    return apiPost<CopilotResponse>('/copilot/ask', request)
  },

  /**
   * Get conversation history
   */
  getHistory: async (limit = 20) => {
    return apiGet<CopilotHistory>('/copilot/history', { limit: String(limit) })
  }
}
