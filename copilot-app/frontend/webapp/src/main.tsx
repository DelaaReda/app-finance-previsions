import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { AppProviders } from './app/providers';
import GlobalErrorBoundary from './components/system/GlobalErrorBoundary';

// Tailwind CSS (must be first for proper cascade)
import './index.css';
import '@fontsource/inter/latin.css';

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
    <GlobalErrorBoundary>
      <AppProviders>
        <App />
      </AppProviders>
    </GlobalErrorBoundary>
  </React.StrictMode>
);
