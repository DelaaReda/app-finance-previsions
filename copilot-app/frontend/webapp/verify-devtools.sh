#!/bin/bash
# Test script to verify React DevTools integration

echo "Verifying React DevTools integration..."

# Check if required files exist
if [ -f "src/debug/reactSnapshot.ts" ]; then
    echo "✓ reactSnapshot.ts created"
else
    echo "✗ reactSnapshot.ts missing"
fi

if [ -f "tools/agent/react-snapshot.ts" ]; then
    echo "✓ react-snapshot.ts created"
else
    echo "✗ react-snapshot.ts missing"
fi

# Check if package.json has the required scripts
if grep -q "dev:devtools" package.json; then
    echo "✓ dev:devtools script added"
else
    echo "✗ dev:devtools script missing"
fi

if grep -q "agent:snapshot" package.json; then
    echo "✓ agent:snapshot script added"
else
    echo "✗ agent:snapshot script missing"
fi

# Check if vite.config.ts has the plugin
if grep -q "injectReactDevTools" vite.config.ts; then
    echo "✓ DevTools injection plugin added"
else
    echo "✗ DevTools injection plugin missing"
fi

echo ""
echo "To test the integration:"
echo "1. Run 'npm run dev:devtools' to start the app with DevTools"
echo "2. Run 'npm run agent:snapshot' to take a React tree snapshot"
echo ""
echo "Note: The DevTools bridge is only active in development mode."