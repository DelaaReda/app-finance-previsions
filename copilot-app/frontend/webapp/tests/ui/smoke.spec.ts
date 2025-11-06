import { test, expect } from '@playwright/test';

test('routes render & widgets not empty', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await expect(page.getByTestId('health-bar')).toBeVisible();

  await page.goto('http://localhost:5173/forecasts');
  await expect(page.getByTestId('forecasts-pro')).toBeVisible();
  await expect(page.getByRole('table')).toBeVisible();

  await page.goto('http://localhost:5173/backtests?strategy=long_top_score');
  await expect(page.getByTestId('backtests-panel')).toBeVisible();
});
