// Types pour le brief et dashboard
import { Source } from './common'

export interface Signal {
  text: string
  pillar: 'macro' | 'technical' | 'news'
  weight: number
}

export interface Pick {
  ticker: string
  rationale: string
  score: number
  type: string
}

export interface BriefData {
  top_signals: Signal[]
  top_risks: Signal[]
  picks: Pick[]
  sources: Source[]
  scores: {
    composite: number
    macro: number
    technical: number
    news: number
  }
  generated_at: string
  period: string
  universe: string[]
}
