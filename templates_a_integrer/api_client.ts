// Robust API client with error boundaries & baseURL logic
export const API_BASE =
  (import.meta as any)?.env?.VITE_API_BASE_URL || '/api';

export async function apiGet(path: string, init?: RequestInit) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, { ...init });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} for ${url}: ${text}`);
  }
  return res.json();
}
