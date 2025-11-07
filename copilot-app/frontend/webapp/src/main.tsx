import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { AppProviders } from './app/providers';
import GlobalErrorBoundary from './components/system/GlobalErrorBoundary';

// Tailwind CSS (must be first for proper cascade)
import './index.css';
import '@fontsource/inter/latin.css';

declare global {
  interface Window {
    ethereum?: unknown;
  }
}

const DISABLE_WEB3 = ((import.meta.env.VITE_DISABLE_WEB3 ?? '1').toString() !== '0');

const scrubEthereum = () => {
  if (typeof window === 'undefined') return;
  if (Object.prototype.hasOwnProperty.call(window, 'ethereum')) {
    try {
      Object.defineProperty(window, 'ethereum', {
        value: undefined,
        configurable: true,
      });
    } catch {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).ethereum = undefined;
      } catch {
        /* ignore */
      }
    }
  }
};

if (typeof window !== 'undefined' && DISABLE_WEB3) {
  scrubEthereum();
  window.addEventListener('ethereum#initialized', scrubEthereum, { once: true });
  console.info('Finance Copilot: Web3 providers disabled (VITE_DISABLE_WEB3=1).');
}

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
