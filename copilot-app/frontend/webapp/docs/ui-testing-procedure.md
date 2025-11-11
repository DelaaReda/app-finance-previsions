# UI Testing Procedure & Quality Assurance Guide

## Overview
This document describes the standard procedure for testing UI pages and resolving common issues that arise during quality assurance.

## Standard Testing Process

### 1. Environment Setup
```bash
# Start services via official script
./finance-copilot.sh start

# Verify all services are running
./finance-copilot.sh status

# Wait for full startup (check logs if needed)
tail -f copilot-app/backend/logs/api.log
```

### 2. Run Automated Tests
```bash
# From frontend directory
cd copilot-app/frontend/webapp
npx playwright test --reporter=line

# For more details
npx playwright test --reporter=html
npx playwright show-report
```

### 3. Manual Verification
- Visit each page: /, /forecasts, /news, /brief, /macro, /stocks, /backtests
- Verify loading/error/empty/loaded states
- Test navigation between pages
- Check responsive design on different screen sizes
- Validate data freshness indicators

## Common Issues & Solutions

### Issue 1: Brittle Selector Matching
**Problem**: Tests fail due to exact text matching (e.g., "Dashboard - Vue d'ensemble" vs "Adaptive Dashboard")
**Solution**: 
- Use `data-testid` attributes instead of text content
- Use regex matching: `getByRole('heading', { name: /Market Brief/i })`
- Add aria-labels to elements with emojis or dynamic content

### Issue 2: API Limit Enforcement
**Problem**: Backend enforces limits (e.g., limit <= 200) but UI sends invalid values
**Solution**:
- Add client-side clamping: `Math.min(userValue, maxValue)`
- Validate input before making API calls
- Inform users of constraints via UI hints

### Issue 3: Empty State Handling
**Problem**: UI crashes with "Cannot read properties of undefined"
**Solution**:
- Use safe access patterns: `data?.property ?? []`
- Apply `ensureArray()` helper to all array access
- Implement ErrorBoundary for graceful fallbacks
- Show proper empty-state UI instead of crashes

### Issue 4: Missing Data Snapshots
**Problem**: Endpoint returns fallback banner "Snapshot indisponible"
**Solution**:
- Check backend scheduler jobs are generating snapshot files
- Verify `data/forecasts.json`, `data/brief_weekly.json`, `data/news_feed.json` exist
- Run manual job if needed to generate initial data
- Set up proper cache fallback system

## Quality Gates Checklist

Before marking any UI task as complete, verify:

- [ ] All page states work (loading, empty, error, success)
- [ ] No JavaScript errors in console
- [ ] Data-testid attributes on interactive elements
- [ ] Never-empty patterns applied (no direct array/object access without guards)
- [ ] Responsive design works mobile/desktop
- [ ] Accessibility attributes present
- [ ] Freshness indicators displayed
- [ ] Error boundaries prevent complete crashes
- [ ] API contracts respected ({ok, data} format)

## Documentation Requirements

For each UI page tested, create documentation artifacts in:
- `proofs/SCREENSHOTS-UI-QA/<PAGE_NAME>/screenshots/`
- `proofs/SCREENSHOTS-UI-QA/<PAGE_NAME>/logs/`
- `proofs/SCREENSHOTS-UI-QA/<PAGE_NAME>/reports/`

Include:
- Screenshots of all 4 states (loading, empty, error, data)
- Console error logs (if any)
- Network response captures
- Performance measurements
- Accessibility validation results

## Resolution Workflow

When issues are identified:

1. **Document**: Take screenshots and save logs showing the problem
2. **Categorize**: Is it a backend issue (empty endpoint), frontend issue (unsafe access), or communication issue?
3. **Fix**: Apply the appropriate solution pattern
4. **Verify**: Run tests again to confirm fix
5. **Report**: Update TASKS_BOARD.md with status and create proof artifacts

## Robust Selectors Guide

Instead of:
```jsx
// Brittle - breaks with content changes
expect(page.locator('text="Dashboard - Vue d\'ensemble"')).toBeVisible();
```

Use:
```jsx
// Robust - survives content changes
expect(page.getByTestId('dashboard-root')).toBeVisible();
expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
```

## Data Protection Patterns

Always use safe access:
```ts
// ❌ Wrong
const items = data.items.map(item => ...);

// ✅ Correct
const items = ensureArray(data?.items).map(item => ...);
const count = safeLength(data?.items);
const config = nn(data?.configuration, defaultConfig);
```

## Expected Outcomes

After following this procedure:
- Zero crashes due to undefined access
- All pages render gracefully in all states
- Tests pass consistently using robust selectors
- Users get meaningful feedback for all conditions
- System remains stable under various data conditions