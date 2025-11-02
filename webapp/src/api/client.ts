// webapp/src/api/client.ts
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
const USE_MOCK = (import.meta.env.VITE_API_MOCK ?? "0") === "1";

function qs(params?: Record<string, any>) {
  if (!params) return "";
  const entries = Object.entries(params).filter(([_, v]) => v !== undefined && v !== null && v !== "");
  return entries.length ? `?${new URLSearchParams(entries as any).toString()}` : "";
}

export async function apiGet<T>(path: string, params?: Record<string, any>): Promise<T> {
  if (USE_MOCK) {
    const mockPath = `/mocks${path}.json`; // ex: /mocks/news/feed.json
    const res = await fetch(mockPath);
    if (!res.ok) throw new Error(`MOCK GET ${mockPath} ${res.status}`);
    return res.json();
  }
  const res = await fetch(`${API_BASE}${path}${qs(params)}`, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`GET ${path} ${res.status}`);
  return res.json();
}

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string }

export async function apiPost<T>(path: string, data?: any): Promise<ApiResult<T>> {
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
  } catch (error) {
    return { ok: false, error: `Network error: ${error.message}` };
  }
}
