import { createContext, ReactNode, useContext } from 'react';

type ColorScheme = 'light' | 'dark';

type ThemeContextType = {
  mode: ColorScheme;
  toggleMode: () => void;
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider = ({ value, children }: { value: ThemeContextType; children: ReactNode }) => (
  <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
);

export const useThemeMode = () => {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useThemeMode must be used within ThemeProvider');
  }
  return ctx;
};
