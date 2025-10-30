/**
 * Types pour les Market Briefs
 * Daily/Weekly briefs avec Top 3 signaux/risques
 */

import { Signal, Source, ScoreBreakdown } from './common.types'
import { MacroIndicator } from './macro.types'
import { NewsItem } from './news.types'

export type MarketBrief = {
  id: string
  type: 'daily' | 'weekly'
  date: string
  title: string
  
  // Top signaux et risques (KPI: Signal > Bruit)
  top_signals: Signal[]      // Top 3
  top_risks: Signal[]         // Top 3
  
  // Snapshots par pilier
  macro_snapshot: MacroSnapshot
  market_snapshot: MarketSnapshot
  news_snapshot: NewsSnapshot
  
  // Résumé exécutif
  executive_summary: string
  key_takeaways: string[]
  
  // Méta
  sources: Source[]
  generated_at: string
  version: string
}

export type MacroSnapshot = {
  headline: string
  key_indicators: MacroIndicator[]
  trend: 'bullish' | 'bearish' | 'neutral'
  alert_level: 'normal' | 'warning' | 'critical'
}

export type MarketSnapshot = {
  headline: string
  top_movers: {
    ticker: string
    change_pct: number
    volume_ratio: number
  }[]
  sector_performance: {
    sector: string
    change_pct: number
  }[]
  market_sentiment: 'bullish' | 'bearish' | 'neutral'
}

export type NewsSnapshot = {
  headline: string
  top_stories: NewsItem[]
  sentiment_breakdown: {
    positive: number
    negative: number
    neutral: number
  }
  trending_topics: string[]
}

export type BriefExportFormat = 'html' | 'pdf' | 'markdown'

export type BriefFilters = {
  type?: 'daily' | 'weekly' | 'all'
  date_from?: string
  date_to?: string
  tickers?: string[]
}
