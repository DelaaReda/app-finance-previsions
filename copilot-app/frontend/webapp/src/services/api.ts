// Client API centralisé (réutilise le client existant)

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

const defaultHeaders = () => ({ 
  'Content-Type': 'application/json', 
  'X-Trace-Id': traceId() 
})

export async function apiGet<T>(
  path: string, 
  params?: Record<string, string>
): Promise<ApiResult<T>> {
  const q = params ? '?' + new URLSearchParams(params).toString() : ''
  try {
    const r = await fetch(`/api${path}${q}`, { headers: defaultHeaders() })
    
    // Check if response is ok (status 200-299)
    if (!r.ok) {
      // Try to get error message from response
      try {
        const errorData = await r.json()
        return { ok: false, error: errorData.error || errorData.detail || `HTTP ${r.status}` }
      } catch {
        // If error response isn't JSON, return status-based error
        return { ok: false, error: `HTTP ${r.status}` }
      }
    }
    
    // Check if response has JSON content
    const contentType = r.headers.get("content-type")
    if (!contentType || !contentType.includes("application/json")) {
      return { ok: false, error: `Expected JSON response for ${path}, got ${contentType}` }
    }
    
    // Parse JSON response safely
    const data = await r.json()
    return { ok: true, data }
  } catch (error) {
    // Network error or parsing error
    return { ok: false, error: error instanceof Error ? error.message : String(error) }
  }
}

export async function apiPost<T>(
  path: string, 
  body: any
): Promise<ApiResult<T>> {
  try {
    const r = await fetch(`/api${path}`, { 
      method: 'POST', 
      headers: defaultHeaders(), 
      body: JSON.stringify(body) 
    })
    
    // Check if response is ok (status 200-299)
    if (!r.ok) {
      // Try to get error message from response
      try {
        const errorData = await r.json()
        return { ok: false, error: errorData.error || errorData.detail || `HTTP ${r.status}` }
      } catch {
        // If error response isn't JSON, return status-based error
        return { ok: false, error: `HTTP ${r.status}` }
      }
    }
    
    // Check if response has JSON content
    const contentType = r.headers.get("content-type")
    if (!contentType || !contentType.includes("application/json")) {
      return { ok: false, error: `Expected JSON response for ${path}, got ${contentType}` }
    }
    
    // Parse JSON response safely
    const data = await r.json()
    return { ok: true, data }
  } catch (error) {
    // Network error or parsing error
    return { ok: false, error: error instanceof Error ? error.message : String(error) }
  }
}
