// webapp/src/types/copilot.types.ts
import { DataSource } from './common.types'

export interface CopilotAskRequest {
  question: string
  context_years?: number
  max_sources?: number
}

export interface CopilotResponse {
  answer: string
  sources: DataSource[]
  confidence: number
  warning?: string
}

export interface Conversation {
  id: string
  timestamp: string
  question: string
  answer: string
  sources: DataSource[]
}

export interface CopilotHistory {
  conversations: Conversation[]
  count: number
}
