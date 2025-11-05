# Pre-push Hook Guide - Finance Copilot

## Purpose

The pre-push hook ensures that all pushes meet quality requirements by running smoke tests automatically before allowing the push to proceed.

## Setup Instructions

### 1. Install the Hook

The pre-push hook is located at `.git/hooks/pre-push` and is automatically executed by git before each push.

### 2. Hook Contents

The hook runs `./scripts/smoke.sh` which tests all critical endpoints:
- `/api/health` - System health status
- `/api/news/feed` - News feed availability
- `/api/forecasts` - Forecast availability  
- `/api/brief/weekly` - Brief endpoint responsiveness
- `/api/backtests` - Backtesting endpoint availability

### 3. Bypass (Emergency Only)

If you need to bypass the smoke test in an emergency:
```bash
BYPASS_SMOKE=1 git push
```

⚠️ **Warning**: Only use bypass for critical emergencies. Regular pushes should always pass smoke tests.

## Troubleshooting

### Hook not executing?
- Ensure the file has execute permissions: `chmod +x .git/hooks/pre-push`
- Check that `scripts/smoke.sh` also has execute permissions: `chmod +x scripts/smoke.sh`

### Tests failing?
- Verify the backend is running via the startup script: `./finance-copilot.sh start`
- Check that all critical endpoints return valid responses
- Review the smoke tests in `scripts/smoke.sh` for any custom requirements

## Maintenance

To update the smoke tests, edit `scripts/smoke.sh` with additional endpoints or change the test criteria as needed.