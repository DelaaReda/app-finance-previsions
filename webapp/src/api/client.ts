export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string }

function traceId(): string {
  const key = 'af-trace-id'
  let t = localStorage.getItem(key)
  if (!t) {
    t = crypto.randomUUID()
    localStorage.setItem(key, t)
  }
  return t
}

const defaultHeaders = () => ({ 'Content-Type': 'application/json', 'X-Trace-Id': traceId() })

// Determine base API URL (use environment variable or default to /api)
const getBaseUrl = (): string => {
  return import.meta.env.VITE_API_BASE_URL || '/api'
}

export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<ApiResult<T>> {
  // Serialize parameters using URLSearchParams
  const q = params ? '?' + new URLSearchParams(params).toString() : ''
  const baseUrl = getBaseUrl()
  const response = await fetch(`${baseUrl}${path}${q}`, { headers: defaultHeaders() })
  
  // Check if response is OK before parsing JSON
  if (!response.ok) {
    return { ok: false, error: `HTTP ${response.status}: ${response.statusText}` }
  }
  
  try {
    const data = await response.json()
    return data
  } catch (error) {
    return { ok: false, error: `JSON parsing error: ${error instanceof Error ? error.message : String(error)}` }
  }
}

export async function apiPost<T>(path: string, body: any): Promise<ApiResult<T>> {
  const baseUrl = getBaseUrl()
  const response = await fetch(`${baseUrl}${path}`, { 
    method: 'POST', 
    headers: defaultHeaders(), 
    body: JSON.stringify(body) 
  })
  
  // Check if response is OK before parsing JSON
  if (!response.ok) {
    return { ok: false, error: `HTTP ${response.status}: ${response.statusText}` }
  }
  
  try {
    const data = await response.json()
    return data
  } catch (error) {
    return { ok: false, error: `JSON parsing error: ${error instanceof Error ? error.message : String(error)}` }
  }
}
