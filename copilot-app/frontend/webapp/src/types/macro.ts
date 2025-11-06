export interface MacroPoint {
  date: string;
  value: number;
}

export type MacroSeriesMap = Record<string, MacroPoint[]>;
