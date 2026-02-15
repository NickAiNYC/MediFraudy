import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Switch,
  FormControlLabel,
  TextField,
  Chip,
  Divider,
  Checkbox,
} from '@mui/material';
import { motion } from 'framer-motion';

const mono = '"JetBrains Mono", monospace';
const bg = '#020617';
const cardBg = '#0f172a';
const surface = '#1e293b';
const borderColor = '#1e293b';
const borderAlt = '#334155';
const textPrimary = '#f1f5f9';
const textSecondary = '#94a3b8';
const textMuted = '#64748b';
const accent = '#10b981';

const sectionVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.12, duration: 0.5, ease: 'easeOut' },
  }),
};

const inputSx = {
  '& .MuiOutlinedInput-root': {
    backgroundColor: surface,
    color: textPrimary,
    fontFamily: mono,
    fontSize: '0.875rem',
    '& fieldset': { borderColor },
    '&:hover fieldset': { borderColor: borderAlt },
    '&.Mui-focused fieldset': { borderColor: accent },
    '&.Mui-disabled': { color: textSecondary, WebkitTextFillColor: textSecondary },
    '&.Mui-disabled fieldset': { borderColor },
  },
  '& .MuiInputLabel-root': { color: textMuted, fontFamily: mono, fontSize: '0.8rem' },
  '& .MuiInputLabel-root.Mui-focused': { color: accent },
};

const Settings: React.FC = () => {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [stateFilter, setStateFilter] = useState('NY');
  const [analysisWindow, setAnalysisWindow] = useState('24 months');
  const [includeCover, setIncludeCover] = useState(true);
  const [includeLegal, setIncludeLegal] = useState(true);
  const [includeFinancial, setIncludeFinancial] = useState(true);

  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: bg, p: 4 }}>
      <Typography
        variant="h4"
        sx={{
          fontWeight: 800,
          fontFamily: mono,
          mb: 4,
          background: `linear-gradient(135deg, ${accent}, #34d399)`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}
      >
        Platform Settings
      </Typography>

      {/* API Configuration */}
      <motion.div custom={0} initial="hidden" animate="visible" variants={sectionVariants}>
        <Card sx={{ backgroundColor: cardBg, border: `1px solid ${borderColor}`, mb: 3, borderRadius: 2 }}>
          <CardContent>
            <Typography sx={{ color: textPrimary, fontFamily: mono, fontWeight: 700, mb: 2 }}>
              API Configuration
            </Typography>
            <Divider sx={{ borderColor, mb: 2 }} />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
              <TextField
                label="API Endpoint"
                value={apiUrl}
                disabled
                size="small"
                sx={{ ...inputSx, flex: 1, minWidth: 280 }}
              />
              <Chip
                label="Connected"
                size="small"
                sx={{
                  backgroundColor: 'rgba(16,185,129,0.15)',
                  color: accent,
                  fontFamily: mono,
                  fontWeight: 600,
                  border: `1px solid ${accent}`,
                }}
              />
            </Box>
          </CardContent>
        </Card>
      </motion.div>

      {/* Data Settings */}
      <motion.div custom={1} initial="hidden" animate="visible" variants={sectionVariants}>
        <Card sx={{ backgroundColor: cardBg, border: `1px solid ${borderColor}`, mb: 3, borderRadius: 2 }}>
          <CardContent>
            <Typography sx={{ color: textPrimary, fontFamily: mono, fontWeight: 700, mb: 2 }}>
              Data Settings
            </Typography>
            <Divider sx={{ borderColor, mb: 2 }} />
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': { color: accent },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { backgroundColor: accent },
                    }}
                  />
                }
                label={<Typography sx={{ color: textSecondary, fontFamily: mono, fontSize: '0.875rem' }}>Auto-refresh data</Typography>}
              />
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <TextField
                  label="Default State Filter"
                  value={stateFilter}
                  onChange={(e) => setStateFilter(e.target.value)}
                  size="small"
                  sx={{ ...inputSx, width: 180 }}
                />
                <TextField
                  label="Analysis Window"
                  value={analysisWindow}
                  onChange={(e) => setAnalysisWindow(e.target.value)}
                  size="small"
                  sx={{ ...inputSx, width: 180 }}
                />
              </Box>
            </Box>
          </CardContent>
        </Card>
      </motion.div>

      {/* Export Settings */}
      <motion.div custom={2} initial="hidden" animate="visible" variants={sectionVariants}>
        <Card sx={{ backgroundColor: cardBg, border: `1px solid ${borderColor}`, mb: 3, borderRadius: 2 }}>
          <CardContent>
            <Typography sx={{ color: textPrimary, fontFamily: mono, fontWeight: 700, mb: 2 }}>
              Export Settings
            </Typography>
            <Divider sx={{ borderColor, mb: 2 }} />
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              {[
                { label: 'Include cover page', checked: includeCover, setter: setIncludeCover },
                { label: 'Include legal framework', checked: includeLegal, setter: setIncludeLegal },
                { label: 'Include financial analysis', checked: includeFinancial, setter: setIncludeFinancial },
              ].map(({ label, checked, setter }) => (
                <FormControlLabel
                  key={label}
                  control={
                    <Checkbox
                      checked={checked}
                      onChange={(e) => setter(e.target.checked)}
                      sx={{ color: textMuted, '&.Mui-checked': { color: accent } }}
                    />
                  }
                  label={<Typography sx={{ color: textSecondary, fontFamily: mono, fontSize: '0.875rem' }}>{label}</Typography>}
                />
              ))}
            </Box>
          </CardContent>
        </Card>
      </motion.div>

      {/* About */}
      <motion.div custom={3} initial="hidden" animate="visible" variants={sectionVariants}>
        <Card sx={{ backgroundColor: cardBg, border: `1px solid ${borderColor}`, borderRadius: 2 }}>
          <CardContent>
            <Typography sx={{ color: textPrimary, fontFamily: mono, fontWeight: 700, mb: 2 }}>
              About
            </Typography>
            <Divider sx={{ borderColor, mb: 2 }} />
            <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {[
                { label: 'Version', value: 'v0.2.0' },
                { label: 'Dataset', value: 'DOGE Feb 2026' },
                { label: 'Claims Analyzed', value: '77.3M' },
              ].map(({ label, value }) => (
                <Box key={label}>
                  <Typography sx={{ color: textMuted, fontFamily: mono, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: 1 }}>
                    {label}
                  </Typography>
                  <Typography sx={{ color: textPrimary, fontFamily: mono, fontWeight: 600, fontSize: '1rem' }}>
                    {value}
                  </Typography>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      </motion.div>
    </Box>
  );
};

export default Settings;
