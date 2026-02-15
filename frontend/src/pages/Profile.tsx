import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Avatar,
  Chip,
  TextField,
  Divider,
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
    '&.Mui-disabled': { color: textSecondary, WebkitTextFillColor: textSecondary },
    '&.Mui-disabled fieldset': { borderColor },
  },
  '& .MuiInputLabel-root': { color: textMuted, fontFamily: mono, fontSize: '0.8rem' },
};

const activities = [
  { action: 'Analyzed Provider #12345', time: '2 hours ago' },
  { action: 'Generated DOJ Report', time: '5 hours ago' },
  { action: 'Flagged Brooklyn Cluster', time: '1 day ago' },
];

const Profile: React.FC = () => {
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
        Analyst Profile
      </Typography>

      {/* Avatar & Role */}
      <motion.div custom={0} initial="hidden" animate="visible" variants={sectionVariants}>
        <Card sx={{ backgroundColor: cardBg, border: `1px solid ${borderColor}`, mb: 3, borderRadius: 2 }}>
          <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap' }}>
            <Avatar
              sx={{
                width: 80,
                height: 80,
                backgroundColor: accent,
                fontSize: '1.8rem',
                fontFamily: mono,
                fontWeight: 700,
              }}
            >
              MF
            </Avatar>
            <Box>
              <Typography sx={{ color: textPrimary, fontFamily: mono, fontWeight: 700, fontSize: '1.25rem' }}>
                MediFraudy Analyst
              </Typography>
              <Chip
                label="Lead Fraud Analyst"
                size="small"
                sx={{
                  mt: 1,
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

      {/* Info Fields */}
      <motion.div custom={1} initial="hidden" animate="visible" variants={sectionVariants}>
        <Card sx={{ backgroundColor: cardBg, border: `1px solid ${borderColor}`, mb: 3, borderRadius: 2 }}>
          <CardContent>
            <Typography sx={{ color: textPrimary, fontFamily: mono, fontWeight: 700, mb: 2 }}>
              Information
            </Typography>
            <Divider sx={{ borderColor, mb: 2 }} />
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {[
                { label: 'Name', value: 'MediFraudy Analyst' },
                { label: 'Email', value: 'analyst@medifraudy.com' },
                { label: 'Organization', value: 'Fraud Detection Unit' },
                { label: 'Clearance', value: 'Level 4 - Full Access' },
              ].map(({ label, value }) => (
                <TextField
                  key={label}
                  label={label}
                  value={value}
                  disabled
                  size="small"
                  fullWidth
                  sx={inputSx}
                />
              ))}
            </Box>
          </CardContent>
        </Card>
      </motion.div>

      {/* Recent Activity */}
      <motion.div custom={2} initial="hidden" animate="visible" variants={sectionVariants}>
        <Card sx={{ backgroundColor: cardBg, border: `1px solid ${borderColor}`, borderRadius: 2 }}>
          <CardContent>
            <Typography sx={{ color: textPrimary, fontFamily: mono, fontWeight: 700, mb: 2 }}>
              Recent Activity
            </Typography>
            <Divider sx={{ borderColor, mb: 2 }} />
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {activities.map(({ action, time }, idx) => (
                <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor: accent,
                      flexShrink: 0,
                    }}
                  />
                  <Box sx={{ flex: 1 }}>
                    <Typography sx={{ color: textPrimary, fontFamily: mono, fontSize: '0.875rem' }}>
                      {action}
                    </Typography>
                    <Typography sx={{ color: textMuted, fontFamily: mono, fontSize: '0.7rem' }}>
                      {time}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      </motion.div>
    </Box>
  );
};

export default Profile;
