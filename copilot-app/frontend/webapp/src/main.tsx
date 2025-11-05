import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { AppProviders } from './app/providers';
import { ErrorBoundary } from './components/system/ErrorBoundary'; // Import global error boundary

// Conditionally import debug utilities in development
if (process.env.NODE_ENV === 'development') {
  import('./debug/reactSnapshot');
}

// Create root element
const container = document.getElementById('root');
if (!container) {
  throw new Error('Failed to find the root element');
}
const root = createRoot(container);

// Render the app wrapped in global error boundary
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <AppProviders>
        <App />
      </AppProviders>
    </ErrorBoundary>
  </React.StrictMode>
);