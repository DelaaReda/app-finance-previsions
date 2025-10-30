/**
 * Types pour le Pilier 1: MACRO
 * FRED, VIX, GSCPI, GPR, inflation, emploi, liquidité
 */

import { Source } from './common.types'

export type MacroSeries = {
  series_id: string
  name: string
  description?: string
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'annual'
  unit?: string
  source: Source
  data: MacroDataPoint[]
  last_updated: string
}

export type MacroDataPoint = {
  date: string
  value: number
  change_pct?: number
  change_abs?: number
}

export type MacroIndicator = {
  id: string
  name: string
  category: 'inflation' | 'employment' | 'liquidity' | 'rates' | 'sentiment' | 'other'
  current_value: number
  previous_value: number
  change_pct: number
  trend: 'up' | 'down' | 'stable'
  alert_level?: 'normal' | 'warning' | 'critical'
  source: Source
  timestamp: string
}

export type MacroDashboard = {
  vix: MacroIndicator
  gscpi: MacroIndicator
  gpr: MacroIndicator
  fed_funds_rate: MacroIndicator
  unemployment: MacroIndicator
  cpi: MacroIndicator
  m2_supply: MacroIndicator
  custom_indicators: MacroIndicator[]
  last_updated: string
}
