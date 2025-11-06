export const API_BASE =
  (import.meta.env?.VITE_API_BASE_URL as string) ||
  '/api';

export const USE_MOCKS = String(import.meta.env?.VITE_USE_MOCKS ?? 'false') === 'true';
export const ENABLE_SSE = String(import.meta.env?.VITE_ENABLE_SSE ?? 'true') === 'true';

export const NET = {
  timeoutMs: 15000,
  retry: 1,
  staleForecastsMs: 60_000,
  staleMacroMs: 5 * 60_000,
  staleNewsMs: 60_000,
  staleBacktestsMs: 60_000,
} as const;

