// UI Health Report using Playwright
// Usage: DASH_BASE=http://127.0.0.1:8050 node ops/ui/ui_health_report.mjs

import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

let chromium
try {
  ;({ chromium } = await import('playwright'))
} catch (e) {
  console.error(JSON.stringify({ ok: false, error: 'playwright-not-installed', hint: 'npm i -D playwright && npx playwright install chromium' }))
  process.exit(1)
}

const BASE = (process.env.DASH_BASE || 'http://127.0.0.1:8050').replace(/\/$/, '')
const PAGES = [
  { path: '/', expect: [{ type: 'text', sel: 'h3', contains: 'Dashboard' }] },
  { path: '/dashboard', expect: [{ type: 'exists', sel: '#dash-top-final' }] },
  { path: '/signals', expect: [{ type: 'exists', sel: '#signals-table' }] },
  { path: '/portfolio', expect: [{ type: 'exists', sel: '#port-proposal' }] },
  { path: '/forecasts', expect: [{ type: 'exists', sel: '#forecasts-content' }] },
  { path: '/deep_dive', expect: [{ type: 'exists', sel: '#deep-dive-ticker' }] },
  { path: '/backtests', expect: [{ type: 'anyOf', sels: ['#backtests-topn-curve', '#backtests-charts', 'table', '.dbc'] }] },
  { path: '/evaluation', expect: [{ type: 'exists', sel: '#evaluation-table' }] },
  { path: '/agents', expect: [{ type: 'text', sel: 'h3', contains: 'Agents Status' }] },
  { path: '/quality', expect: [{ type: 'text', sel: 'h3', contains: 'Qualité des données' }] },
  { path: '/observability', expect: [{ type: 'exists', sel: '#dash-http-status' }] },
  { path: '/regimes', expect: [{ type: 'text', sel: 'h3', contains: 'Regimes' }] },
  { path: '/risk', expect: [{ type: 'text', sel: 'h3', contains: 'Risk' }] },
  { path: '/recession', expect: [{ type: 'text', sel: 'h3', contains: 'Recession' }] },
]

function todayDt() {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}${mm}${dd}`
}

async function main() {
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  const results = []

  const shotsDir = 'artifacts/ui_health'
  await mkdir(shotsDir, { recursive: true })

  for (const item of PAGES) {
    const url = BASE + item.path
    const entry = { path: item.path, url, ok: true, warnings: [], errors: [], ms: 0 }
    const t0 = Date.now()
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 })
      // Quick check: any Dash error banner
      const errBanner = await page.locator('.dash-error-menu').count()
      if (errBanner > 0) entry.warnings.push('dash-error-menu visible')
      // If an explicit danger alert is rendered, treat as error
      const dangerCnt = await page.locator('.alert-danger').count()
      if (dangerCnt > 0) {
        entry.errors.push('alert-danger visible')
        entry.ok = false
      }

      for (const exp of item.expect) {
        if (exp.type === 'exists') {
          // simple retry to avoid race conditions
          let count = 0
          for (let i = 0; i < 5; i++) {
            count = await page.locator(exp.sel).count()
            if (count > 0) break
            await page.waitForTimeout(300)
          }
          if (count === 0) {
            entry.errors.push(`missing ${exp.sel}`)
            entry.ok = false
          }
        } else if (exp.type === 'text') {
          const el = page.locator(exp.sel).first()
          const has = await el.count()
          if (!has) {
            entry.errors.push(`missing ${exp.sel}`)
            entry.ok = false
          } else {
            const txt = (await el.textContent()) || ''
            if (!txt.includes(exp.contains)) {
              entry.warnings.push(`text '${exp.contains}' not found in ${exp.sel}`)
            }
          }
        } else if (exp.type === 'anyOf') {
          let found = false
          for (const s of exp.sels) {
            let cnt = 0
            for (let i = 0; i < 5; i++) {
              cnt = await page.locator(s).count()
              if (cnt > 0) break
              await page.waitForTimeout(300)
            }
            if (cnt > 0) { found = true; break }
          }
          if (!found) {
            entry.errors.push(`none of selectors present: ${exp.sels.join(', ')}`)
            entry.ok = false
          }
        }
      }
      const slug = item.path === '/' ? 'root' : item.path.replace(/^\//, '').replace(/\//g, '_')
      const shot = join(shotsDir, `${slug}.png`)
      await page.screenshot({ path: shot, fullPage: true })
    } catch (e) {
      entry.ok = false
      entry.errors.push(String(e))
    } finally {
      entry.ms = Date.now() - t0
      results.push(entry)
    }
  }

  await browser.close()

  const report = { ok: results.every(r => r.ok), base: BASE, asof: new Date().toISOString(), results }
  const outPath = join('data', 'reports', `dt=${todayDt()}`, 'ui_health_report.json')
  await mkdir(outPath.substring(0, outPath.lastIndexOf('/')), { recursive: true })
  await writeFile(outPath, JSON.stringify(report, null, 2), 'utf-8')
  console.log(JSON.stringify(report, null, 2))
}

main().catch(e => { console.error(JSON.stringify({ ok: false, error: String(e) })); process.exit(1) })
