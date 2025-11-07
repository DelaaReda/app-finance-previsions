import type { ApiResponse } from '@/types/common.types';

const RAW_API_BASE = ((import.meta.env as any).VITE_API_BASE_URL ?? '/api').trim();
const API_BASE = RAW_API_BASE;
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
  const { method = 'GET', searchParams, body, signal, timeoutMs = 15_000 } = opts ?? {};
  const url = buildUrl(path, searchParams);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

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

    if (response.status === 204) return undefined as T;

    const data = (await response.json()) as unknown;
    if (data && typeof data === 'object' && 'data' in (data as any)) {
      return (data as any).data as T;
    }
    return data as T;
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      emitDebug({
        type: 'http',
        url,
        method,
        message: `Request timeout after ${timeoutMs}ms: ${url}`,
      });
      throw new Error(`Request timeout after ${timeoutMs}ms: ${url}`);
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
  try {
    const data = await api.fetchJson<T>(path, {
      searchParams: params,
      timeoutMs: options?.timeoutMs,
      signal: options?.signal,
    });
    return { ok: true, data };
  } catch (error: any) {
    return { ok: false, error: error?.message ?? String(error) };
  }
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<ApiResponse<T>> {
  try {
    const data = await api.fetchJson<T>(path, {
      method: 'POST',
      body,
      timeoutMs: options?.timeoutMs,
      signal: options?.signal,
    });
    return { ok: true, data };
  } catch (error: any) {
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
