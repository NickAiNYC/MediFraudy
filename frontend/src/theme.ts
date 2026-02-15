import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#10b981', // emerald-500
      light: '#34d399',
      dark: '#059669',
    },
    secondary: {
      main: '#3b82f6', // blue-500
      light: '#60a5fa',
      dark: '#2563eb',
    },
    error: {
      main: '#ef4444', // red-500
      light: '#f87171',
      dark: '#dc2626',
    },
    warning: {
      main: '#f59e0b', // amber-500
      light: '#fbbf24',
      dark: '#d97706',
    },
    info: {
      main: '#3b82f6', // blue-500
      light: '#60a5fa',
      dark: '#2563eb',
    },
    success: {
      main: '#10b981', // emerald-500
      light: '#34d399',
      dark: '#059669',
    },
    background: {
      default: '#020617', // slate-950
      paper: '#0f172a', // slate-900
    },
    text: {
      primary: '#f1f5f9', // slate-100
      secondary: '#94a3b8', // slate-400
    },
    divider: '#1e293b', // slate-800
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
    subtitle1: { fontWeight: 500, color: '#94a3b8' },
    subtitle2: { fontWeight: 500, fontSize: '0.875rem', color: '#94a3b8' },
    body1: { fontWeight: 400 },
    body2: { fontWeight: 400, fontSize: '0.875rem' },
    caption: { fontSize: '0.75rem', color: '#64748b' },
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
          backgroundImage: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          border: '1px solid #1e293b',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
          transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
          '&:hover': {
            borderColor: '#334155',
            boxShadow: '0 10px 15px rgba(0,0,0,0.15)',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 600,
          backgroundColor: '#1e293b',
          color: '#94a3b8',
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          letterSpacing: '0.05em',
        },
        body: {
          borderBottomColor: '#1e293b',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: '#0f172a',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#0f172a',
          borderBottom: '1px solid #1e293b',
          boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#0f172a',
          borderRight: '1px solid #1e293b',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          fontSize: '0.75rem',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
});

export default theme;

