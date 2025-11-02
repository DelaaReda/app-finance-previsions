# 🤖 AGENT-BASED REACT DEBUGGING

## 📋 OVERVIEW

This guide explains how to use the agent-based React debugging tools for the Finance Copilot application. This approach uses a Playwright-based agent to programmatically inspect the React component tree and extract debugging information.

## 🔧 SETUP

### 1. Verify Installation
The required tools are already installed in `package.json`:

```json
{
  "devDependencies": {
    "react-devtools": "^5.x",
    "playwright": "^1.x",
    "tsx": "^4.x",
    "concurrently": "^9.x"
  }
}
```

### 2. Verify Installation
```bash
cd frontend/webapp
npm install
npx playwright install chromium
```

## 🚀 QUICK START

### 1. Start the Application with DevTools
```bash
# Terminal 1: This starts both React DevTools and the frontend
cd frontend/webapp
npm run dev:devtools
```

This command:
- Launches React DevTools standalone app
- Starts the Vite development server
- Injects DevTools bridge script automatically

### 2. Run Agent-Based Diagnostics
```bash
# Terminal 2: Run snapshot while app is running
cd frontend/webapp
npm run agent:snapshot
```

## 📊 AGENT SNAPSHOT COMMANDS

### Basic Component Tree Snapshot
```bash
npm run agent:snapshot
```
This returns a complete JSON representation of the React component tree with:
- Component names
- Props (safely serialized)
- State (safely serialized)
- Child relationships

### Environment Variables
- `APP_URL`: Override default URL (default: http://localhost:5173)
- `DEVTOOLS_ENABLED`: Explicitly disable injection (default: true in dev)

## 🔍 DIAGNOSTIC ANALYSIS

### Automated Checks
The agent includes automated diagnostic functions in `tools/agent/checks.ts`:

```typescript
// Find components with large props
findPropBloat(tree, [], [])

// Find anonymous components
findAnonymous(tree, [], [])
```

### Custom Diagnostics
Create custom diagnostic scripts in the `tools/agent/` directory:

```typescript
// tools/agent/custom-diagnostic.ts
async function customDiagnostic() {
  // Your diagnostic logic here
  const result = await page.evaluate(() => {
    return window.__DUMP_REACT_TREE__();
  });
  
  // Process and analyze results
  console.log('Custom analysis results:', result);
}
```

## ⚡ ADVANCED USAGE

### 1. Manual Script Injection (Alternative)
If the Vite plugin doesn't work, manually inject the script:

```html
<!-- Add to index.html in development only -->
<script src="http://localhost:8097"></script>
```

### 2. Direct Hook Access
The agent exposes the React DevTools hook in development:

```typescript
// In the browser context
window.__DUMP_REACT_TREE__() // Returns component tree
```

### 3. Programmatic Analysis
Create scripts to analyze specific components or patterns:

```bash
# Run custom analysis
npx tsx tools/agent/analyze-dashboard.ts
```

## 🎯 USE CASES FOR FINANCE COPILOT

### 1. Dashboard Component Analysis
```bash
# Check dashboard component structure
npm run agent:snapshot | jq '.trees[] | select(.name == "Dashboard")'
```

### 2. Performance Bottleneck Detection
```bash
# Identify components with large props
npm run agent:snapshot | npx tsx tools/agent/checks.ts findPropBloat
```

### 3. State Verification
```bash
# Verify state of specific components
npm run agent:snapshot | jq '.trees[] | select(.name == "MarketBrief").state'
```

## 🔧 TROUBLESHOOTING

### Issue: "DevTools hook not available"
**Cause**: React DevTools bridge not connected
**Solution**: 
1. Verify `react-devtools` is running (port 8097)
2. Check that the script is injected in HTML
3. Ensure app is running in development mode

### Issue: Empty Component Tree
**Cause**: React hasn't initialized or DevTools hook not available
**Solution**:
1. Wait for full React app initialization
2. Refresh the page
3. Check that `__REACT_DEVTOOLS_GLOBAL_HOOK__` is available in browser console

### Issue: Serialization Errors
**Cause**: Complex objects in props/state causing JSON issues
**Solution**: The agent includes safe serialization that handles functions and complex objects

## 🛡️ SECURITY MEASURES

### 1. Development Only
- Bridge script injection limited to `NODE_ENV=development`
- Disabled when `DEVTOOLS_ENABLED=false`
- No bridge in production builds

### 2. Safe Serialization
- Functions and complex objects safely serialized as `[Function]` or `[DepthLimit]`
- Prevents information leakage through JSON output

## 📚 REFERENCE

### Files
- `src/debug/reactSnapshot.ts` - Core snapshot utility
- `tools/agent/react-snapshot.ts` - Playwright-based agent
- `tools/agent/checks.ts` - Diagnostic functions
- `vite.config.ts` - DevTools injection plugin
- `DEVTOOLS.md` - Comprehensive usage guide

### Commands
- `npm run dev:devtools` - Start app with DevTools
- `npm run agent:snapshot` - Take component tree snapshot
- `APP_URL=http://example.com npm run agent:snapshot` - Snapshot different URL

This agent-based approach allows for programmatic React component inspection and automated diagnostics without requiring manual browser interaction.