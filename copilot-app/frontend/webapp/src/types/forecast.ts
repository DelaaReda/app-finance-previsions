export type Horizon = 'short' | 'medium' | 'long';
export type Direction = 'up' | 'down' | 'neutral' | 'flat';

export type ForecastComponents = Record<string, number>;

export interface ForecastSparkPoint {
  date: string;
  value: number | null;
}

export interface ForecastExplain {
  top_features?: Array<{ name: string; weight: number }>;
}

export interface ForecastItem {
  ticker: string;
  name?: string | null;
  sector?: string | null;
  horizon: Horizon;
  themes?: string[];
  score: number; // 0..100
  direction: Direction;
  confidence: number; // 0..1
  confidence_pct?: number | null;
  expected_return_pct?: number | null;
  expectedReturnPct?: number | null; // camelCase alias
  expectedReturn?: number | null; // 0..1 for legacy consumers
  forecasted_at?: string | null;
  forecastedAt?: string | null; // camelCase alias
  model_version?: string | null;
  components?: ForecastComponents;
  sparkline?: ForecastSparkPoint[];
  explain?: ForecastExplain;

  // Legacy aliases kept for backwards compatibility with existing widgets
  symbol?: string; // alias for ticker
  updatedAt?: string | null;
}

export interface ForecastsResponse {
  updated_at?: string | null;
  request_id?: string | null;
  count: number;
  items: ForecastItem[];
}
