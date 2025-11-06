import type { ApiResponse } from '@/types/common.types';

const API_BASE = (import.meta.env as any).VITE_API_BASE_URL ?? '/api';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

function buildUrl(path: string, searchParams?: Record<string, string | number | boolean | undefined>) {
  const base = API_BASE.endsWith('/') ? API_BASE : `${API_BASE}/`;
  const url = new URL(path.replace(/^\//, ''), base);
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
      throw new Error(`HTTP ${response.status} ${response.statusText} — ${text || url}`);
    }

    if (response.status === 204) return undefined as T;

    const data = (await response.json()) as unknown;
    if (data && typeof data === 'object' && 'data' in (data as any)) {
      return (data as any).data as T;
    }
    return data as T;
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeoutMs}ms: ${url}`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  fetchJson,
  buildUrl,
};

export async function apiGet<T>(path: string, params?: Record<string, any>): Promise<ApiResponse<T>> {
  try {
    const data = await api.fetchJson<T>(path, { searchParams: params });
    return { ok: true, data };
  } catch (error: any) {
    return { ok: false, error: error?.message ?? String(error) };
  }
}

export async function apiPost<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
  try {
    const data = await api.fetchJson<T>(path, { method: 'POST', body });
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
