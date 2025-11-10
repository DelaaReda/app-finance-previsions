import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

function ensureDir(dir: string) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

const sizes = [
  { name: '1366x768', width: 1366, height: 768 },
  { name: '1440x900', width: 1440, height: 900 },
  { name: '1920x1080', width: 1920, height: 1080 },
];

test.describe('Desktop responsive snapshots', () => {
  for (const s of sizes) {
    test(`dashboard ${s.name}`, async ({ page }) => {
      await page.setViewportSize({ width: s.width, height: s.height });
      await page.goto('/');
      await page.waitForTimeout(500); // allow layout paint

      const date = new Date();
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, '0');
      const dd = String(date.getDate()).padStart(2, '0');
      const outDir = path.resolve(process.cwd(), '../../proofs', `ui-${yyyy}-${mm}-${dd}`, 'desktop');
      ensureDir(outDir);

      const file = path.join(outDir, `dashboard-${s.name}.png`);
      await page.screenshot({ path: file, fullPage: false });
      expect(fs.existsSync(file)).toBeTruthy();
    });
  }
});

