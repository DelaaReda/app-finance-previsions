// webapp/src/api/client.ts
import type { ApiResponse } from '../types/common'

const API_BASE = (import.meta.env as any).VITE_API_BASE_URL ?? "8050/api";

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
  try {
    const res = await fetch(`${API_BASE}${path}${qs(params)}`, { headers: { Accept: "application/json" } });
    
    // Check response status
    if (!res.ok) {
      // Try to get error message from response body, if available
      const contentType = res.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        try {
          const errorData = await res.json();
          return { ok: false, error: `GET ${path} ${res.status}: ${errorData.detail || errorData.error || errorData.message || 'Request failed'}` };
        } catch {
          // If error response isn't JSON, return status-based error
          return { ok: false, error: `GET ${path} ${res.status}` };
        }
      }
      return { ok: false, error: `GET ${path} ${res.status}` };
    }
    
    // Check if response has JSON content
    const contentType = res.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      return { ok: false, error: `Expected JSON for ${path}, got ${contentType}` };
    }
    
    // Ensure response has body before parsing
    if (res.status === 204 || res.headers.get('content-length') === '0') {
      return { ok: true, data: undefined as any };
    }
    
    try {
      return { ok: true, data: await res.json() };
    } catch (parseError: any) {
      return { ok: false, error: `Failed to parse JSON from ${path}: ${parseError.message}` };
    }
  } catch (error: any) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return { ok: false, error: `Network error: Unable to reach server for ${path}` };
    }
    return { ok: false, error: `Network error: ${error.message}` };
  }
}

export async function apiPost<T>(path: string, data?: any): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(data),
    });
    
    // Check response status
    if (!res.ok) {
      // Try to get error message from response body, if available
      const contentType = res.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        try {
          const errorData = await res.json();
          return { ok: false, error: `POST ${path} ${res.status}: ${errorData.detail || errorData.error || errorData.message || 'Request failed'}` };
        } catch {
          // If error response isn't JSON, return status-based error
          return { ok: false, error: `POST ${path} ${res.status}` };
        }
      }
      return { ok: false, error: `POST ${path} ${res.status}` };
    }
    
    // Check if response has JSON content
    const contentType = res.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      return { ok: false, error: `Expected JSON for ${path}, got ${contentType}` };
    }
    
    // Ensure response has body before parsing
    if (res.status === 204 || res.headers.get('content-length') === '0') {
      return { ok: true, data: undefined as any };
    }
    
    try {
      const result = await res.json();
      return { ok: true, data: result };
    } catch (parseError: any) {
      return { ok: false, error: `Failed to parse JSON from ${path}: ${parseError.message}` };
    }
  } catch (error: any) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return { ok: false, error: `Network error: Unable to reach server for ${path}` };
    }
    return { ok: false, error: `Network error: ${error.message}` };
  }
}
