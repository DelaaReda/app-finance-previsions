// webapp/src/api/client.ts
import type { ApiResponse } from '../types/common'

const API_BASE = (import.meta as any).env.VITE_API_BASE_URL ?? "/api";
const USE_MOCK = ((import.meta as any).env.VITE_API_MOCK ?? "0") === "1";

function qs(params?: Record<string, any>) {
  if (!params) return "";
  
  const normalizedParams: Record<string, string> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      if (Array.isArray(value)) {
        // Handle arrays by joining with commas
        normalizedParams[key] = value.join(',');
      } else {
        normalizedParams[key] = String(value);
      }
    }
  }
  
  const entries = Object.entries(normalizedParams);
  return entries.length ? `?${new URLSearchParams(entries as any).toString()}` : "";
}

export async function apiGet<T>(path: string, params?: Record<string, any>): Promise<ApiResponse<T>> {
  if (USE_MOCK) {
    const mockPath = `/mocks${path}.json`; // ex: /mocks/news/feed.json
    const res = await fetch(mockPath);
    if (!res.ok) return { ok: false, error: `MOCK GET ${mockPath} ${res.status}` };
    return { ok: true, data: await res.json() };
  }
  try {
    const res = await fetch(`${API_BASE}${path}${qs(params)}`, { headers: { Accept: "application/json" } });
    if (!res.ok) return { ok: false, error: `GET ${path} ${res.status}` };
    return { ok: true, data: await res.json() };
  } catch (error: any) {
    return { ok: false, error: `Network error: ${error.message}` };
  }
}

export async function apiPost<T>(path: string, data?: any): Promise<ApiResponse<T>> {
  if (USE_MOCK) {
    // For mock, we'll treat POSTs as GETs with query params
    const params = data ? { ...data, _method: 'POST' } : {};
    const mockPath = `/mocks${path}.json`;
    const res = await fetch(mockPath + qs(params));
    if (!res.ok) return { ok: false, error: `MOCK POST ${mockPath} ${res.status}` };
    return { ok: true, data: await res.json() };
  }
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(data),
    });
    
    if (!res.ok) return { ok: false, error: `POST ${path} ${res.status}` };
    
    const result = await res.json();
    return { ok: true, data: result };
  } catch (error: any) {
    return { ok: false, error: `Network error: ${error.message}` };
  }
}
