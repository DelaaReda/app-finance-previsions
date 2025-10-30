// webapp/src/types/macro.types.ts
export interface MacroSeries {
  series: string
  date: string
  value: number
}

export interface MacroSnapshot {
  [seriesId: string]: number
}

export interface MacroIndicators {
  cpi_yoy: number | null
  yield_curve_10y_2y: number | null
  recession_probability: number | null
  vix: number | null
}
