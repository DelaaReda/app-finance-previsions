// Simple URL screenshot utility using Playwright Chromium
// Usage:
//   URL=http://localhost:5556 OUT=artifacts/ui_health/legacy_forecasts.png node ops/ui/snap_url.mjs

import { mkdir } from 'node:fs/promises'
import { dirname } from 'node:path'

let chromium
try { ({ chromium } = await import('playwright')) } catch (e) {
  console.error('Playwright not installed. Run: npm i -D playwright && npx playwright install chromium')
  process.exit(1)
}

const url = process.env.URL
const out = process.env.OUT || 'artifacts/ui_health/snap.png'
if (!url) {
  console.error('Missing URL env. Example: URL=http://localhost:5556 node ops/ui/snap_url.mjs')
  process.exit(2)
}

await mkdir(dirname(out), { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 })
await page.screenshot({ path: out, fullPage: true })
await browser.close()
console.log(`Saved screenshot to ${out}`)

