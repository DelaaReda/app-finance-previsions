// Types pour le pilier Macro (FRED, VIX, GSCPI, GPR)

import { Source } from './common.types'

export type MacroIndicator = {
  id: string
  name: string
  symbol: string // Ex: FRED:UNRATE, VIX, GSCPI
  value: number
  previousValue: number
  change: number // % de changement
  changePercent: number
  timestamp: string
  source: Source
  unit?: string
  category: MacroCategory
}

export type MacroCategory = 
  | 'inflation'
  | 'employment'
  | 'liquidity'
  | 'volatility'
  | 'geopolitical'
  | 'commodities'
  | 'interest_rates'

export type MacroSeries = {
  indicator: MacroIndicator
  timeseries: TimeSeriesPoint[]
  trend: 'up' | 'down' | 'stable'
  regime?: string // Ex: "expansion", "contraction"
}

export type TimeSeriesPoint = {
  date: string
  value: number
}

export type MacroDashboard = {
  indicators: MacroIndicator[]
  alerts: MacroAlert[]
  regime: {
    current: string
    confidence: number
    changeDate: string
  }
  lastUpdate: string
}

export type MacroAlert = {
  indicator: string
  type: 'threshold' | 'trend_change' | 'anomaly'
  severity: 'low' | 'medium' | 'high'
  message: string
  timestamp: string
}
