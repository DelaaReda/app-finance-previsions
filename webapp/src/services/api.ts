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
  const r = await fetch(`/api${path}${q}`, { headers: defaultHeaders() })
  return r.json()
}

export async function apiPost<T>(
  path: string, 
  body: any
): Promise<ApiResult<T>> {
  const r = await fetch(`/api${path}`, { 
    method: 'POST', 
    headers: defaultHeaders(), 
    body: JSON.stringify(body) 
  })
  return r.json()
}
