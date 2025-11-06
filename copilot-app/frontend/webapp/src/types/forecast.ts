export type Horizon = 'short' | 'medium' | 'long';
export type Direction = 'up' | 'down' | 'flat';

export interface ForecastItem {
  symbol: string;
  horizon: Horizon;
  score: number;
  direction: Direction;
  confidence?: number;
  expectedReturn?: number;
  updatedAt?: string;
}
