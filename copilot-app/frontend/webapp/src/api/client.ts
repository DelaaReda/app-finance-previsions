import type { ApiResponse } from '@/types/common.types';

const RAW_API_BASE = ((import.meta.env as any).VITE_API_BASE_URL ?? '/api').trim();
const API_BASE = (() => {
  const raw = RAW_API_BASE;
  // Local static-serve fallback: if running on 5173 and base is relative, use backend 8050
  try {
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    const isDevStatic = /localhost:5173|127\.0\.0\.1:5173|0\.0\.0\.0:5173/.test(origin);
    if ((!raw || !/^https?:\/\//i.test(raw)) && isDevStatic) {
      return 'http://localhost:8050';
    }
  } catch {}
  return raw;
})();
const DEBUG_EVENT = 'finance-debug:event';
const DEBUG_ENABLED = ((import.meta.env as any).VITE_APP_DEBUG ?? '0').toString() !== '0';

const RELATIVE_BASE_PATH = (() => {
  if (!RAW_API_BASE || RAW_API_BASE.startsWith('http')) return null;
  const cleaned = RAW_API_BASE.replace(/\/+$/, '');
  return cleaned.startsWith('/') ? cleaned.slice(1) : cleaned;
})();

type DebugPayload = {
  type: 'http';
  url: string;
  method: string;
  message: string;
  status?: number;
};

function emitDebug(payload: DebugPayload) {
  if (!DEBUG_ENABLED || typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(DEBUG_EVENT, { detail: payload }));
}

function resolveBase() {
  const raw = API_BASE ?? '/api';
  if (/^https?:\/\//i.test(raw)) {
    return raw.endsWith('/') ? raw : `${raw}/`;
  }

  const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173';
  const normalized = raw.startsWith('/') ? raw : `/${raw}`;
  return `${origin}${normalized.endsWith('/') ? normalized : `${normalized}/`}`;
}

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function normalizePath(path: string) {
  if (!path) return '';
  let normalized = path.trim().replace(/^\/+/, '');
  if (RELATIVE_BASE_PATH) {
    const pattern = new RegExp(`^${escapeRegExp(RELATIVE_BASE_PATH)}(?:/|$)`, 'i');
    normalized = normalized.replace(pattern, '');
  }
  return normalized;
}

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

function buildUrl(path: string, searchParams?: Record<string, string | number | boolean | undefined>) {
  const base = resolveBase();
  const url = new URL(normalizePath(path), base);
  if (searchParams) {
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

async function fetchJson<T>(
  path: string,
  opts?: {
    method?: HttpMethod;
    searchParams?: Record<string, string | number | boolean | undefined>;
    body?: unknown;
    signal?: AbortSignal;
    timeoutMs?: number;
  },
): Promise<T> {
  // Default timeout: 15s for most endpoints, but longer for slow endpoints
  const defaultTimeout = 15_000;
  const { method = 'GET', searchParams, body, signal, timeoutMs = defaultTimeout } = opts ?? {};
  
  // Increase timeout for slow endpoints
  let effectiveTimeout = timeoutMs;
  if (path.includes('/api/macro/series')) {
    effectiveTimeout = 30_000; // 30s for macro (FRED can be slow)
  } else if (path.includes('/api/forecasts') || path.includes('/api/brief/')) {
    effectiveTimeout = 25_000; // 25s for forecasts/brief (can be slow)
  } else if (path.includes('/api/backtests')) {
    effectiveTimeout = 60_000; // 60s for backtests (computation heavy)
  } else if (path.includes('/api/intelligence/') || path.includes('/api/recommendations/')) {
    effectiveTimeout = 30_000; // 30s for intelligence/recommendations (can be slow with LLM)
  }
  const url = buildUrl(path, searchParams);
  const startTime = performance.now();

  // Development logging
  if (DEBUG_ENABLED || import.meta.env.DEV) {
    console.log(`[API] 📤 ${method} ${url}`, {
      method,
      path,
      searchParams,
      timeout: effectiveTimeout,
      hasBody: !!body
    });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), effectiveTimeout);

  try {
    const response = await fetch(url, {
      method,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: signal ?? controller.signal,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      const message = `HTTP ${response.status} ${response.statusText} — ${text || url}`;
      emitDebug({ type: 'http', url, method, message, status: response.status });
      throw new Error(message);
    }

    const elapsed = performance.now() - startTime;
    
    if (DEBUG_ENABLED || import.meta.env.DEV) {
      console.log(`[API] ✅ ${method} ${url} - ${response.status} (${elapsed.toFixed(0)}ms)`);
    }

    if (response.status === 204) return undefined as T;

    const data = (await response.json()) as unknown;
    
    if (DEBUG_ENABLED || import.meta.env.DEV) {
      const dataSize = JSON.stringify(data).length;
      console.log(`[API] 📦 Response data size: ${(dataSize / 1024).toFixed(2)}KB`, {
        hasData: !!(data && typeof data === 'object' && 'data' in (data as any)),
        keys: data && typeof data === 'object' ? Object.keys(data as any).slice(0, 5) : []
      });
    }
    
    if (data && typeof data === 'object' && 'data' in (data as any)) {
      return (data as any).data as T;
    }
    return data as T;
  } catch (error: any) {
    const elapsed = performance.now() - startTime;
    
    if (DEBUG_ENABLED || import.meta.env.DEV) {
      console.error(`[API] ❌ ${method} ${url} - Error after ${elapsed.toFixed(0)}ms`, {
        error: error?.message || String(error),
        errorType: error?.name,
        errorStack: error?.stack?.split('\n').slice(0, 3)
      });
    }
    
    if (error?.name === 'AbortError') {
      const isBackendDown = error?.message?.includes('Failed to fetch') || 
                            error?.message?.includes('NetworkError') ||
                            error?.message?.includes('ERR_CONNECTION_REFUSED');
      
      emitDebug({
        type: 'http',
        url,
        method,
        message: isBackendDown 
          ? `Backend unavailable: ${url} (check if backend is running on port 8050)`
          : `Request timeout after ${effectiveTimeout}ms: ${url}`,
      });
      
      throw new Error(
        isBackendDown
          ? `Backend unavailable. Please ensure the backend is running on http://localhost:8050`
          : `Request timeout after ${effectiveTimeout}ms: ${url}`
      );
    }
    
    // Check for connection errors (backend not running)
    if (error?.message?.includes('Failed to fetch') || 
        error?.message?.includes('NetworkError') ||
        error?.message?.includes('ERR_CONNECTION_REFUSED')) {
      emitDebug({
        type: 'http',
        url,
        method,
        message: `Backend unavailable: ${url} (check if backend is running on port 8050)`,
      });
      throw new Error(`Backend unavailable. Please ensure the backend is running on http://localhost:8050`);
    }
    
    emitDebug({
      type: 'http',
      url,
      method,
      message: error?.message ?? String(error),
    });
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  fetchJson,
  buildUrl,
};

type RequestOptions = {
  timeoutMs?: number;
  signal?: AbortSignal;
};

export async function apiGet<T>(
  path: string,
  params?: Record<string, any>,
  options?: RequestOptions,
): Promise<ApiResponse<T>> {
  if (DEBUG_ENABLED || import.meta.env.DEV) {
    console.log(`[API] 🔵 GET ${path}`, { params, options });
  }
  
  try {
    const data = await api.fetchJson<T>(path, {
      searchParams: params,
      timeoutMs: options?.timeoutMs,
      signal: options?.signal,
    });
    
    if (DEBUG_ENABLED || import.meta.env.DEV) {
      console.log(`[API] ✅ GET ${path} - Success`, { 
        dataType: typeof data,
        isArray: Array.isArray(data),
        size: data && typeof data === 'object' ? Object.keys(data).length : 'N/A'
      });
    }
    
    return { ok: true, data };
  } catch (error: any) {
    if (DEBUG_ENABLED || import.meta.env.DEV) {
      console.error(`[API] ❌ GET ${path} - Failed`, { 
        error: error?.message || String(error),
        params 
      });
    }
    return { ok: false, error: error?.message ?? String(error) };
  }
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<ApiResponse<T>> {
  if (DEBUG_ENABLED || import.meta.env.DEV) {
    console.log(`[API] 🟢 POST ${path}`, { 
      bodySize: body ? JSON.stringify(body).length : 0,
      hasBody: !!body 
    });
  }
  
  try {
    const data = await api.fetchJson<T>(path, {
      method: 'POST',
      body,
      timeoutMs: options?.timeoutMs,
      signal: options?.signal,
    });
    
    if (DEBUG_ENABLED || import.meta.env.DEV) {
      console.log(`[API] ✅ POST ${path} - Success`);
    }
    
    return { ok: true, data };
  } catch (error: any) {
    if (DEBUG_ENABLED || import.meta.env.DEV) {
      console.error(`[API] ❌ POST ${path} - Failed`, { 
        error: error?.message || String(error) 
      });
    }
    return { ok: false, error: error?.message ?? String(error) };
  }
}

export const client = {
  async get<T>(path: string): Promise<T> {
    return api.fetchJson<T>(path);
  },
  async post<T>(path: string, body?: unknown): Promise<T> {
    return api.fetchJson<T>(path, { method: 'POST', body });
  },
};

export { API_BASE };
