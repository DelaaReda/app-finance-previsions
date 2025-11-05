import { createTheme, responsiveFontSizes } from '@mui/material/styles';

// Custom palette for finance-themed colors
// Avoid strict Palette typing here for now to keep theme augmentation simple in this repo
declare module '@mui/material/styles' {
  interface Palette {
    finance: any;
  }
  interface PaletteOptions {
    finance?: any;
  }
}

declare module '@mui/material' {
  interface Color {
    50?: string;
    100?: string;
    200?: string;
    300?: string;
    400?: string;
    500?: string;
    600?: string;
    700?: string;
    800?: string;
    900?: string;
  }
}

// Define custom color palette for financial app
const customPalette = {
  // Bullish/positive colors (greens)
  bullish: {
    main: '#2e7d32',
    light: '#60ad5e',
    dark: '#1b5e20',
    contrastText: '#fff',
  },
  // Bearish/negative colors (reds)
  bearish: {
    main: '#d32f2f',
    light: '#ff6659',
    dark: '#9a0007',
    contrastText: '#fff',
  },
  // Neutral colors
  neutral: {
    main: '#616161',
    light: '#8e8e8e',
    dark: '#373737',
    contrastText: '#fff',
  },
  // Primary brand color (blue for financial trust)
  primaryBrand: {
    main: '#1976d2',
    light: '#63a4ff',
    dark: '#004ba0',
    contrastText: '#fff',
  },
  // Secondary brand color (purple for analytics)
  secondaryBrand: {
    main: '#9c27b0',
    light: '#d05ce3',
    dark: '#6a0080',
    contrastText: '#fff',
  }
};

export const lightTheme = responsiveFontSizes(
  createTheme({
    palette: {
      mode: 'light',
      primary: {
        main: customPalette.primaryBrand.main,
        light: customPalette.primaryBrand.light,
        dark: customPalette.primaryBrand.dark,
        contrastText: customPalette.primaryBrand.contrastText,
      },
      secondary: {
        main: customPalette.secondaryBrand.main,
        light: customPalette.secondaryBrand.light,
        dark: customPalette.secondaryBrand.dark,
        contrastText: customPalette.secondaryBrand.contrastText,
      },
      success: {
        main: customPalette.bullish.main,
        light: customPalette.bullish.light,
        dark: customPalette.bullish.dark,
        contrastText: customPalette.bullish.contrastText,
      },
      error: {
        main: customPalette.bearish.main,
        light: customPalette.bearish.light,
        dark: customPalette.bearish.dark,
        contrastText: customPalette.bearish.contrastText,
      },
      warning: {
        main: '#ff9800',
        light: '#ffc947',
        dark: '#c66900',
        contrastText: 'rgba(0, 0, 0, 0.87)',
      },
      info: {
        main: '#2196f3',
        light: '#64b5f6',
        dark: '#1976d2',
        contrastText: '#fff',
      },
      background: {
        default: '#f5f7fa',
        paper: '#ffffff',
      },
      text: {
        primary: 'rgba(0, 0, 0, 0.87)',
        secondary: 'rgba(0, 0, 0, 0.6)',
        disabled: 'rgba(0, 0, 0, 0.38)',
      },
      divider: 'rgba(0, 0, 0, 0.12)',
    },
    typography: {
      fontFamily: [
        'Roboto',
        'Arial',
        'sans-serif',
        '"Apple Color Emoji"',
        '"Segoe UI Emoji"',
        '"Segoe UI Symbol"',
      ].join(','),
      h1: {
        fontWeight: 500,
        fontSize: '2.5rem',
        lineHeight: 1.2,
      },
      h2: {
        fontWeight: 500,
        fontSize: '2rem',
        lineHeight: 1.3,
      },
      h3: {
        fontWeight: 500,
        fontSize: '1.75rem',
        lineHeight: 1.3,
      },
      h4: {
        fontWeight: 500,
        fontSize: '1.5rem',
        lineHeight: 1.4,
      },
      h5: {
        fontWeight: 500,
        fontSize: '1.25rem',
        lineHeight: 1.4,
      },
      h6: {
        fontWeight: 500,
        fontSize: '1.125rem',
        lineHeight: 1.5,
      },
      button: {
        textTransform: 'none', // Keep buttons in natural case
        fontWeight: 500,
      },
      caption: {
        fontSize: '0.75rem',
      },
      body1: {
        fontSize: '0.875rem',
      },
      body2: {
        fontSize: '0.75rem',
      },
    },
    components: {
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: '#fff',
            color: 'rgba(0, 0, 0, 0.87)',
            boxShadow: '0px 2px 4px -1px rgba(0,0,0,0.06), 0px 4px 5px 0px rgba(0,0,0,0.06), 0px 1px 10px 0px rgba(0,0,0,0.10)',
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            boxShadow: '0px 2px 1px -1px rgba(0,0,0,0.06), 0px 1px 1px 0px rgba(0,0,0,0.06), 0px 1px 3px 0px rgba(0,0,0,0.08)',
          },
        },
      },
      MuiDataGrid: {
        styleOverrides: {
          root: {
            border: 'none',
            '& .MuiDataGrid-columnHeader': {
              backgroundColor: 'rgba(25, 118, 210, 0.04)', // primary light at 4%
              fontWeight: 600,
            },
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 600,
            color: 'rgba(0, 0, 0, 0.87)',
          },
        },
      },
    },
    spacing: 8, // Default spacing unit
  })
);

export const darkTheme = responsiveFontSizes(
  createTheme({
    palette: {
      mode: 'dark',
      primary: {
        main: customPalette.primaryBrand.light,
        light: '#90caf9',
        dark: customPalette.primaryBrand.main,
        contrastText: '#fff',
      },
      secondary: {
        main: customPalette.secondaryBrand.light,
        light: '#ce93d8',
        dark: customPalette.secondaryBrand.main,
        contrastText: '#fff',
      },
      success: {
        main: customPalette.bullish.light,
        light: '#a5d6a7',
        dark: customPalette.bullish.main,
        contrastText: 'rgba(0, 0, 0, 0.87)',
      },
      error: {
        main: customPalette.bearish.light,
        light: '#ef9a9a',
        dark: customPalette.bearish.main,
        contrastText: '#fff',
      },
      warning: {
        main: '#ffb74d',
        light: '#ffe0b2',
        dark: '#f57c00',
        contrastText: 'rgba(0, 0, 0, 0.87)',
      },
      info: {
        main: '#4fc3f7',
        light: '#81d4fa',
        dark: '#0288d1',
        contrastText: 'rgba(0, 0, 0, 0.87)',
      },
      background: {
        default: '#121212',
        paper: '#1e1e1e',
      },
      text: {
        primary: '#fff',
        secondary: 'rgba(255, 255, 255, 0.7)',
        disabled: 'rgba(255, 255, 255, 0.5)',
      },
      divider: 'rgba(255, 255, 255, 0.12)',
    },
    typography: {
      fontFamily: [
        'Roboto',
        'Arial',
        'sans-serif',
        '"Apple Color Emoji"',
        '"Segoe UI Emoji"',
        '"Segoe UI Symbol"',
      ].join(','),
      h1: {
        fontWeight: 400,
        fontSize: '2.5rem',
        lineHeight: 1.2,
      },
      h2: {
        fontWeight: 400,
        fontSize: '2rem',
        lineHeight: 1.3,
      },
      h3: {
        fontWeight: 400,
        fontSize: '1.75rem',
        lineHeight: 1.3,
      },
      h4: {
        fontWeight: 400,
        fontSize: '1.5rem',
        lineHeight: 1.4,
      },
      h5: {
        fontWeight: 400,
        fontSize: '1.25rem',
        lineHeight: 1.4,
      },
      h6: {
        fontWeight: 500,
        fontSize: '1.125rem',
        lineHeight: 1.5,
      },
      button: {
        textTransform: 'none',
        fontWeight: 500,
      },
      caption: {
        fontSize: '0.75rem',
      },
      body1: {
        fontSize: '0.875rem',
      },
      body2: {
        fontSize: '0.75rem',
      },
    },
    components: {
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: '#1e1e1e',
            color: '#fff',
            boxShadow: '0px 2px 4px -1px rgba(0,0,0,0.16), 0px 4px 5px 0px rgba(0,0,0,0.14), 0px 1px 10px 0px rgba(0,0,0,0.12)',
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            boxShadow: '0px 2px 1px -1px rgba(0,0,0,0.20), 0px 1px 1px 0px rgba(0,0,0,0.14), 0px 1px 3px 0px rgba(0,0,0,0.12)',
          },
        },
      },
      MuiDataGrid: {
        styleOverrides: {
          root: {
            border: 'none',
            '& .MuiDataGrid-columnHeader': {
              backgroundColor: 'rgba(25, 118, 210, 0.16)', // primary dark at 16%
              fontWeight: 600,
            },
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 600,
            color: '#fff',
          },
        },
      },
    },
    spacing: 8,
  })
);

/**
 * Theme builder function that returns the appropriate theme based on mode
 * @param mode - 'light' or 'dark'
 * @returns MUI theme object
 */
export function buildTheme(mode: 'light' | 'dark') {
  return mode === 'light' ? lightTheme : darkTheme;
}

// Also export the default theme (light theme) as fallback
export default lightTheme;