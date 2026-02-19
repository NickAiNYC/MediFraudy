import { useState, useEffect } from 'react';
import { createTheme, Theme } from '@mui/material/styles';

export type ThemeMode = 'dark' | 'light';

const createCustomTheme = (mode: ThemeMode): Theme => {
  const isDark = mode === 'dark';

  return createTheme({
    palette: {
      mode,
      primary: {
        main: '#10b981',
        light: '#34d399',
        dark: '#059669',
      },
      secondary: {
        main: '#3b82f6',
        light: '#60a5fa',
        dark: '#2563eb',
      },
      error: {
        main: '#ef4444',
        light: '#f87171',
        dark: '#dc2626',
      },
      warning: {
        main: '#f59e0b',
        light: '#fbbf24',
        dark: '#d97706',
      },
      info: {
        main: '#3b82f6',
        light: '#60a5fa',
        dark: '#2563eb',
      },
      success: {
        main: '#10b981',
        light: '#34d399',
        dark: '#059669',
      },
      background: {
        default: isDark ? '#020617' : '#f8fafc',
        paper: isDark ? '#0f172a' : '#ffffff',
      },
      text: {
        primary: isDark ? '#f1f5f9' : '#0f172a',
        secondary: isDark ? '#94a3b8' : '#64748b',
      },
      divider: isDark ? '#1e293b' : '#e2e8f0',
    },
    typography: {
      fontFamily: [
        'Inter',
        '-apple-system',
        'BlinkMacSystemFont',
        '"Segoe UI"',
        'sans-serif',
      ].join(','),
      h1: { fontSize: '2.5rem', fontWeight: 800, letterSpacing: '-0.025em' },
      h2: { fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.025em' },
      h3: { fontSize: '1.75rem', fontWeight: 700 },
      h4: { fontSize: '1.5rem', fontWeight: 700 },
      h5: { fontSize: '1.25rem', fontWeight: 600 },
      h6: { fontSize: '1rem', fontWeight: 600 },
    },
    shape: {
      borderRadius: 12,
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            borderRadius: 8,
            fontWeight: 600,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 12,
            backgroundImage: isDark
              ? 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)'
              : 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
            border: isDark ? '1px solid #1e293b' : '1px solid #e2e8f0',
            boxShadow: isDark
              ? '0 4px 6px rgba(0,0,0,0.1)'
              : '0 1px 3px rgba(0,0,0,0.1)',
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            backgroundColor: isDark ? '#0f172a' : '#ffffff',
          },
        },
      },
    },
  });
};

export const useTheme = () => {
  const [mode, setMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('theme-mode');
    return (saved as ThemeMode) || 'dark';
  });

  const [theme, setTheme] = useState<Theme>(() => createCustomTheme(mode));

  useEffect(() => {
    localStorage.setItem('theme-mode', mode);
    setTheme(createCustomTheme(mode));
  }, [mode]);

  const toggleTheme = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return { theme, mode, toggleTheme };
};
