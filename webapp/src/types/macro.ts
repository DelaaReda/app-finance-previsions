// Types pour les données macro (Pilier 1)
import { TimeSeriesPoint } from './common'

export interface MacroSeries {
  data: TimeSeriesPoint[]
  yoy: TimeSeriesPoint[] | null
  source: string
  generated_at: string
}

export interface MacroSeriesResponse {
  [seriesId: string]: MacroSeries
}
