/**
 * Zod Validation Wrapper for React Query Hooks
 *
 * This module provides runtime schema validation for backend API responses.
 * It helps detect schema drift early and provides clear error messages.
 *
 * Usage:
 * ```typescript
 * const { data } = useQuery({
 *   queryKey: ['forecasts'],
 *   queryFn: async () => {
 *     const response = await fetch('/api/forecasts');
 *     const json = await response.json();
 *     return validateData(json, ForecastsResponseSchema);
 *   }
 * });
 * ```
 *
 * Author: CLAUDE-CODE
 * Task: FC-PHASE3-001 - Playwright Contract Guards + Zod Validation
 */

import { z } from 'zod';

/**
 * Enable/disable validation based on environment
 * Set to false in production to skip validation overhead
 */
const VALIDATION_ENABLED = import.meta.env.MODE !== 'production';

/**
 * Validation error handler
 */
export class ValidationError extends Error {
  constructor(
    message: string,
    public zodError: z.ZodError,
    public data: unknown
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}

/**
 * Generic validation wrapper
 */
export function validateData<T>(data: unknown, schema: z.ZodSchema<T>): T {
  if (!VALIDATION_ENABLED) {
    return data as T;
  }

  const result = schema.safeParse(data);

  if (!result.success) {
    console.error('❌ Zod Validation Failed:', {
      errors: result.error.errors,
      data,
    });

    throw new ValidationError(
      `Schema validation failed: ${result.error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join(', ')}`,
      result.error,
      data
    );
  }

  return result.data;
}

// ==============================================================================
// Forecast Schemas
// ==============================================================================

export const HorizonSchema = z.enum(['short', 'medium', 'long']);
export const DirectionSchema = z.enum(['up', 'down', 'neutral', 'flat']);

export const ForecastSparkPointSchema = z.object({
  date: z.string(),
  value: z.number().nullable(),
});

export const ForecastExplainSchema = z.object({
  top_features: z.array(
    z.object({
      name: z.string(),
      weight: z.number(),
    })
  ).optional(),
});

export const ForecastItemSchema = z.object({
  ticker: z.string(),
  name: z.string().nullable().optional(),
  sector: z.string().nullable().optional(),
  horizon: HorizonSchema,
  themes: z.array(z.string()).optional(),
  score: z.number().min(0).max(100),
  direction: DirectionSchema,
  confidence: z.number().min(0).max(1),
  confidence_pct: z.number().nullable().optional(),
  expected_return_pct: z.number().nullable().optional(),
  expectedReturnPct: z.number().nullable().optional(),
  expectedReturn: z.number().nullable().optional(),
  forecasted_at: z.string().nullable().optional(),
  forecastedAt: z.string().nullable().optional(),
  model_version: z.string().nullable().optional(),
  components: z.record(z.number()).optional(),
  sparkline: z.array(ForecastSparkPointSchema).optional(),
  explain: ForecastExplainSchema.optional(),
  // Legacy aliases
  symbol: z.string().optional(),
  updatedAt: z.string().nullable().optional(),
  top_features: z.array(
    z.object({
      name: z.string(),
      importance: z.number(),
      value: z.number().optional(),
    })
  ).optional(),
  reason: z.string().optional(),
});

export const ForecastsResponseSchema = z.object({
  updated_at: z.string().nullable().optional(),
  request_id: z.string().nullable().optional(),
  count: z.number().min(0),
  items: z.array(ForecastItemSchema),
});

// ==============================================================================
// Backtests Schemas
// ==============================================================================

export const BacktestsResponseSchema = z.object({
  request_id: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
  params: z.object({
    strategy: z.string(),
    universe: z.string().nullable().optional(),
    benchmark: z.string().nullable().optional(),
    horizon: z.enum(['short', 'medium', 'long']).nullable().optional(),
  }),
  kpis: z.object({
    cagr_pct: z.number(),
    sharpe: z.number(),
    sortino: z.number(),
    max_drawdown_pct: z.number(),
    win_rate_pct: z.number(),
    volatility_pct: z.number(),
    exposure_pct: z.number().optional(),
    avg_trade_pct: z.number().optional(),
  }),
  equity_curve: z.array(
    z.object({
      date: z.string(),
      strategy: z.number().nullable(),
      benchmark: z.number().nullable().optional(),
    })
  ),
  drawdowns: z.array(
    z.object({
      date: z.string(),
      dd_pct: z.number().nullable(),
    })
  ).optional(),
  monthly_returns: z.array(
    z.object({
      month: z.string(),
      pct: z.number().nullable(),
    })
  ).optional(),
  trades_sample: z.array(
    z.object({
      enter: z.string(),
      exit: z.string(),
      ticker: z.string(),
      ret_pct: z.number().nullable(),
    })
  ).optional(),
});

// ==============================================================================
// News Schemas
// ==============================================================================

export const NewsArticleSchema = z.object({
  id: z.string().optional(),
  title: z.string(),
  url: z.string(),
  source: z.string().optional(),
  publishedAt: z.string().optional(),
  published_at: z.string().optional(),
  sentiment: z.enum(['pos', 'neg', 'neu']).optional(),
  summary: z.string().optional(),
  tickers: z.array(z.string()).optional(),
});

export const NewsResponseSchema = z.object({
  articles: z.array(NewsArticleSchema),
  total: z.number().optional(),
  updated_at: z.string().nullable().optional(),
});

// ==============================================================================
// Health Schemas
// ==============================================================================

export const DatasetHealthSchema = z.object({
  name: z.string(),
  status: z.enum(['healthy', 'stale', 'missing']),
  last_updated: z.string().nullable().optional(),
  latency_seconds: z.number().optional(),
  row_count: z.number().optional(),
  size_mb: z.number().optional(),
});

export const HealthResponseSchema = z.object({
  status: z.enum(['operational', 'degraded', 'down']),
  datasets: z.array(DatasetHealthSchema),
  updated_at: z.string().optional(),
});

/**
 * Legacy Health Response (used by /api/health endpoint)
 */
export const LegacyHealthDataSchema = z.object({
  status: z.enum(['up', 'down', 'degraded']),
  backend_up: z.boolean().optional(),
  last_updates: z.record(z.string()).optional(),
  data_paths: z.record(z.string()).optional(),
  timestamp: z.string().optional(),
  version: z.string().optional(),
  message: z.string().optional(),
  error: z.string().optional(),
});

/**
 * DatasetHealth for useHealth hook
 */
export const DatasetHealthItemSchema = z.object({
  name: z.string(),
  last_update: z.string(),
  latency_sec: z.number(),
  errors_24h: z.number(),
});

/**
 * Health response for useHealth hook
 */
export const HealthSchema = z.object({
  updated_at: z.string().optional(),
  datasets: z.array(DatasetHealthItemSchema),
  thresholds: z.object({
    stale_sec: z.record(z.number()).optional(),
  }).optional(),
});

// ==============================================================================
// Helper Functions for Common Validations
// ==============================================================================

/**
 * Validate that response has at least one item
 */
export function assertHasItems<T>(data: T[], context: string): T[] {
  if (!VALIDATION_ENABLED) return data;

  if (data.length === 0) {
    console.warn(`⚠️ ${context}: Response has 0 items (expected > 0)`);
  }

  return data;
}

/**
 * Validate that all required fields are present
 */
export function assertRequiredFields<T extends Record<string, unknown>>(
  obj: T,
  fields: Array<keyof T>,
  context: string
): T {
  if (!VALIDATION_ENABLED) return obj;

  const missing = fields.filter(field => obj[field] === undefined || obj[field] === null);

  if (missing.length > 0) {
    console.warn(`⚠️ ${context}: Missing required fields: ${missing.join(', ')}`);
  }

  return obj;
}

/**
 * Validate numeric range
 */
export function assertInRange(
  value: number,
  min: number,
  max: number,
  context: string
): number {
  if (!VALIDATION_ENABLED) return value;

  if (value < min || value > max) {
    console.warn(`⚠️ ${context}: Value ${value} outside range [${min}, ${max}]`);
  }

  return value;
}

/**
 * Log validation success for debugging
 */
export function logValidationSuccess(context: string, itemCount?: number): void {
  if (VALIDATION_ENABLED) {
    const countStr = itemCount !== undefined ? ` (${itemCount} items)` : '';
    console.log(`✅ Validation passed: ${context}${countStr}`);
  }
}
