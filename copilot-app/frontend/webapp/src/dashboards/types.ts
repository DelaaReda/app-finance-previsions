export type WidgetType =
  | 'metric'
  | 'line'
  | 'area'
  | 'barlist'
  | 'donut'
  | 'table'
  | 'sparkline';

export type DataKind = 'macro' | 'forecasts' | 'news';

export interface DashboardContext {
  horizon: 'short' | 'medium' | 'long';
  universe: string[];
  themes?: string[];
  macroIds?: string[];
}

export interface WidgetBase {
  id: string;
  type: WidgetType;
  title?: string;
  description?: string;
  colSpan?: number;
  height?: number;
  dataTestId?: string;
  data: {
    kind: DataKind;
    params?: Record<string, any>;
    mapping?: Record<string, any>;
  };
}

export interface Section {
  id: string;
  title?: string;
  subtitle?: string;
  widgets: WidgetBase[];
}

export interface DashboardTemplate {
  slug: string;
  title: string;
  description?: string;
  defaultContext: DashboardContext;
  layout: Section[];
}
