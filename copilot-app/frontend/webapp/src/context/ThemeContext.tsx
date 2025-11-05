import React, { createContext, useContext, ReactNode, useEffect, useState } from 'react';
import { ThemeProvider as MuiThemeProvider, createTheme } from '@mui/material/styles';
import { buildTheme } from '../theme';

interface ThemeContextType {
  mode: 'light' | 'dark';
  toggleMode: () => void;
  theme: ReturnType<typeof createTheme>; // Use correct type for theme
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useThemeMode = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemeMode must be used within a ThemeProvider');
  }
  return context;
};

interface ThemeProviderProps {
  children: ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  // Get initial mode from localStorage or system preference
  const getInitialMode = (): 'light' | 'dark' => {
    const saved = localStorage.getItem('palette-mode');
    if (saved === 'light' || saved === 'dark') return saved as 'light' | 'dark';
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  };

  const [mode, setMode] = useState<'light' | 'dark'>(getInitialMode());
  const [theme, setTheme] = useState(() => buildTheme(mode));

  useEffect(() => {
    // Update localStorage when mode changes
    localStorage.setItem('palette-mode', mode);
    // Update theme based on mode
    setTheme(buildTheme(mode));
  }, [mode]);

  const toggleMode = () => {
    setMode(prevMode => prevMode === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ mode, toggleMode, theme }}>
      <MuiThemeProvider theme={theme}>
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
};