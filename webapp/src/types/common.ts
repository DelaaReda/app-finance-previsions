// Types communs pour l'application
export interface ApiResponse<T> {
  ok: boolean
  data?: T
  error?: string
}

export interface TimeSeriesPoint {
  t: string  // ISO date
  v: number | null
}

export interface OHLCVPoint {
  t: string
  o: number | null
  h: number | null
  l: number | null
  c: number | null
  v: number | null
}

export interface Source {
  type: 'macro' | 'technical' | 'news' | 'series'
  [key: string]: any
}
