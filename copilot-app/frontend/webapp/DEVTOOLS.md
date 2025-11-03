# React DevTools Integration

This project includes React DevTools integration for enhanced debugging and diagnostics capabilities. The integration is only active in development mode.

## Usage

### Development with DevTools
```bash
# Start the React DevTools and the application together
npm run dev:devtools
```

This command will:
- Launch the React DevTools standalone app
- Start the Vite development server
- Inject the DevTools bridge script automatically in development mode

### Taking React Tree Snapshots
```bash
# Take a snapshot of the current React component tree
npm run agent:snapshot
```

This command will:
- Open the application in a headless browser
- Extract the React component tree structure
- Output a JSON representation of the tree with props and state

### Environment Variables
- `DEVTOOLS_ENABLED=false`: Explicitly disable DevTools injection (even in development)
- `APP_URL`: Override the default application URL for snapshotting (default: http://localhost:5173)

## Security Notes

- The DevTools bridge script (http://localhost:8097) is only injected in development mode
- The injection is disabled in production builds
- The agent tools are only available in development environments

## Files Added

- `src/debug/reactSnapshot.ts`: Utility functions to dump React tree
- `tools/agent/react-snapshot.ts`: Playwright-based snapshot utility
- `tools/agent/checks.ts`: Diagnostic functions for analyzing the component tree
- `vite.config.ts`: Updated with DevTools injection plugin
- `package.json`: New scripts and dependencies for DevTools integration

## Diagnostics Features

The snapshot utility includes automated checks for:

- Component prop bloat (over 100KB of props)
- Anonymous components
- Component tree structure analysis

Run `npm run agent:snapshot` and pipe the output to diagnostic scripts for automated analysis.