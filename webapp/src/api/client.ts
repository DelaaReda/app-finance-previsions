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
