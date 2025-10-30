export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string }

export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<ApiResult<T>> {
  const q = params ? '?' + new URLSearchParams(params).toString() : ''
  const r = await fetch(`/api${path}${q}`)
  return r.json()
}

export async function apiPost<T>(path: string, body: any): Promise<ApiResult<T>> {
  const r = await fetch(`/api${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  return r.json()
}

