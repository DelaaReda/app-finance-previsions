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

const mantineTheme = createTheme({
  primaryColor: 'indigo',
  defaultRadius: 'md',
  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  headings: {
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontWeight: '700',
  },
  colors: {
    indigo: ['#edf2ff','#dbe4ff','#bac8ff','#91a7ff','#748ffc','#5c7cfa','#4c6ef5','#4263eb','#3b5bdb','#364fc7'],
    teal: ['#e6fcf5','#c3fae8','#96f2d7','#63e6be','#38d9a9','#20c997','#12b886','#0ca678','#099268','#087f5b'],
    slate: ['#f8fafc','#f1f5f9','#e2e8f0','#cbd5f5','#94a3b8','#64748b','#475569','#334155','#1e293b','#0f172a'],
  },
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
