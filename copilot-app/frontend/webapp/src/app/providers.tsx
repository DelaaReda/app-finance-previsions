import React, { useMemo } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { MantineProvider, ColorSchemeScript, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { useLocalStorage } from '@mantine/hooks';
import { ThemeProvider as ThemeProviderWrapper } from '../context/ThemeContext';

// Mantine CSS imports
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import '@mantine/spotlight/styles.css';

// Tremor uses Tailwind CSS (no separate CSS import needed in v3+)

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Mantine theme with professional finance UI/UX
type ColorScheme = 'light' | 'dark';

// Use CSS variables defined in index.css so Tailwind/Mantine share the same tokens.
const mantineTheme = createTheme({
  primaryColor: 'indigo',
  defaultRadius: 'md',
  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  headings: {
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontWeight: '700',
  },
  // Provide a small palette but prefer CSS variables for runtime theming
  colors: {
    // Mantine expects arrays of 10 shades — repeat the CSS var to satisfy the contract.
    indigo: [
      'var(--accent)','var(--accent)','var(--accent)','var(--accent)','var(--accent)',
      'var(--accent)','var(--accent)','var(--accent)','var(--accent)','var(--accent)'
    ] as unknown as [string,string,string,string,string,string,string,string,string,string],
    teal: [
      'var(--accent-2)','var(--accent-2)','var(--accent-2)','var(--accent-2)','var(--accent-2)',
      'var(--accent-2)','var(--accent-2)','var(--accent-2)','var(--accent-2)','var(--accent-2)'
    ] as unknown as [string,string,string,string,string,string,string,string,string,string],
    slate: [
      'var(--surface)','var(--surface)','var(--surface)','var(--surface)','var(--surface)',
      'var(--surface)','var(--surface)','var(--surface)','var(--surface)','var(--surface)'
    ] as unknown as [string,string,string,string,string,string,string,string,string,string],
    // Gray scale for better text contrast in dark mode
    gray: [
      '#1a1f2e', '#2d3441', '#3d4554', '#4e5767', '#5f6a7a', // 0-4: darker shades
      '#8b95a6', '#a8b2c3', '#c5d0e0', '#e2eefd', '#ffffff', // 5-9: lighter shades (better contrast)
    ] as unknown as [string,string,string,string,string,string,string,string,string,string],
  },
  // Note: global body/background is handled by index.css (CSS variables). Mantine colors map to CSS vars above.
  components: {
    Card: {
      defaultProps: {
        shadow: 'md',
        padding: 'lg',
        withBorder: true,
        radius: 'lg',
      },
    },
    Paper: {
      defaultProps: {
        radius: 'lg',
        withBorder: true,
        shadow: 'sm',
      },
    },
    Button: {
      defaultProps: {
        radius: 'md',
        size: 'md',
      },
      styles: {
        root: {
          backgroundImage: 'linear-gradient(90deg, var(--accent), #7c95ff)'
        }
      }
    },
  },
});

// AppProviders component
export const AppProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [colorScheme, setColorScheme] = useLocalStorage<ColorScheme>({
    key: 'finance-copilot-color-scheme',
    defaultValue: 'dark',
    getInitialValueInEffect: false,
  });

  const toggleMode = () => setColorScheme((prev: ColorScheme) => (prev === 'dark' ? 'light' : 'dark'));

  const themeContextValue = useMemo(() => ({ mode: colorScheme, toggleMode }), [colorScheme]);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProviderWrapper value={themeContextValue}>
        <MantineProvider
          theme={mantineTheme}
          defaultColorScheme={colorScheme}
          forceColorScheme={colorScheme}
          withCssVariables
        >
          <ColorSchemeScript defaultColorScheme="dark" />
          <Notifications position="top-right" />
          {children}
          <ReactQueryDevtools initialIsOpen={false} />
        </MantineProvider>
      </ThemeProviderWrapper>
    </QueryClientProvider>
  );
};
