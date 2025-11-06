import { test, expect } from '@playwright/test'

// Helper to parse JSON and assert ok
async function json<T>(resp: any): Promise<T> {
  expect(resp.ok()).toBeTruthy()
  const data = await resp.json()
  return data as T
}

test.describe('Integration Data (no mocks)', () => {
  test('health endpoint up and dashboard loads', async ({ page }) => {
    const r = await page.request.get('/api/health')
    const body = await json<any>(r)
    const payload = body?.data ?? body
    expect(payload).toBeTruthy()
    expect((payload.backend_up === true) || (payload.status === 'up')).toBeTruthy()

    await page.goto('/')
    await expect(page.getByTestId('dashboard-root')).toBeVisible()
  })

  test('macro series returns rows and macro widgets render', async ({ page }) => {
    const r = await page.request.get('/api/macro/series?limit=50')
    const raw = await json<any>(r)
    const rows = raw?.data ?? raw
    expect(Array.isArray(rows)).toBeTruthy()
    expect((rows as any[]).length).toBeGreaterThan(0)

    await page.goto('/macro')
    await expect(page.getByTestId('macro-board')).toBeVisible()
  })

  test('news feed returns articles and News page lists cards', async ({ page }) => {
    const r = await page.request.get('/api/news/feed', {
      params: { tickers: 'SPY,QQQ', limit: '50', sort: 'recent' },
    } as any)
    const feed = await json<any>(r)
    const payload = feed?.data ?? feed
    const articles = Array.isArray(payload?.articles) ? payload.articles : []
    expect(articles.length).toBeGreaterThan(0)

    await page.goto('/news')
    await expect(page.getByText('Filtres')).toBeVisible()
  })

  test('stocks prices returns points and screener renders', async ({ page }) => {
    const r = await page.request.get('/api/stocks/prices', {
      params: { ticker: 'SPY', interval: '1d', downsample: '250' },
    } as any)
    const body = await json<any>(r)
    const points = body?.data?.tickers?.SPY?.points ?? body?.tickers?.SPY?.points ?? []
    expect(Array.isArray(points)).toBeTruthy()
    expect(points.length).toBeGreaterThan(0)

    await page.goto('/stocks')
    await expect(page.getByTestId('stocks-screener')).toBeVisible()
  })

  test('forecasts returns rows and forecasts widget renders', async ({ page }) => {
    const r = await page.request.get('/api/forecasts')
    const body = await json<any>(r)
    const payload = body?.data ?? body
    const rows = payload?.rows ?? []
    expect(Array.isArray(rows)).toBeTruthy()
    expect(rows.length).toBeGreaterThan(0)

    await page.goto('/forecasts')
    await expect(page.getByTestId('forecasts-pro')).toBeVisible()
  })

  test('brief daily returns structured data and Brief page renders', async ({ page }) => {
    const r = await page.request.get('/api/brief/daily')
    const body = await json<any>(r)
    const payload = body?.data ?? body
    expect(payload).toBeTruthy()
    // Expect structure keys to exist
    expect(Array.isArray(payload.top_signals)).toBeTruthy()
    expect(Array.isArray(payload.top_risks)).toBeTruthy()
    // Enforce at least 1 item (integration, no mocks)
    expect(payload.top_signals.length + payload.top_risks.length).toBeGreaterThan(0)

    await page.goto('/brief')
    await expect(page.getByText('Market Brief', { exact: false })).toBeVisible()
  })
})
