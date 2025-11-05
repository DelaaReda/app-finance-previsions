import React from 'react';
import { createRoot } from 'react-dom/client';
import { CssBaseline } from '@mui/material';
import App from './App';
import { AppProviders } from './app/providers';
import { ErrorBoundary } from './components/system/ErrorBoundary';

// Font imports
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

// Create root element
const container = document.getElementById('root');
if (!container) {
  throw new Error('Failed to find the root element');
}
const root = createRoot(container);

// Render the app wrapped in global error boundary and MUI providers
// Theme provider is now handled in AppProviders with ThemeContext
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <AppProviders>
        <CssBaseline />
        <App />
      </AppProviders>
    </ErrorBoundary>
  </React.StrictMode>
);