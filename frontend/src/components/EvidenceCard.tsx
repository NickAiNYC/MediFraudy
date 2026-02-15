import React from 'react';
import { Box, Typography } from '@mui/material';
import { motion } from 'framer-motion';

type Severity = 'critical' | 'high' | 'medium' | 'low';

interface EvidenceCardProps {
  icon: React.ReactNode;
  title: string;
  count: number | string;
  amount: string;
  severity: Severity;
  description: string;
  delay?: number;
}

const severityColors: Record<Severity, { bg: string; border: string; text: string; badge: string }> = {
  critical: {
    bg: 'rgba(239, 68, 68, 0.08)',
    border: 'rgba(239, 68, 68, 0.3)',
    text: '#f87171',
    badge: '#ef4444',
  },
  high: {
    bg: 'rgba(249, 115, 22, 0.08)',
    border: 'rgba(249, 115, 22, 0.3)',
    text: '#fb923c',
    badge: '#f97316',
  },
  medium: {
    bg: 'rgba(245, 158, 11, 0.08)',
    border: 'rgba(245, 158, 11, 0.3)',
    text: '#fbbf24',
    badge: '#f59e0b',
  },
  low: {
    bg: 'rgba(59, 130, 246, 0.08)',
    border: 'rgba(59, 130, 246, 0.3)',
    text: '#60a5fa',
    badge: '#3b82f6',
  },
};

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  icon,
  title,
  count,
  amount,
  severity,
  description,
  delay = 0,
}) => {
  const colors = severityColors[severity];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      <Box
        sx={{
          background: colors.bg,
          borderRadius: 3,
          p: 3,
          border: `1px solid ${colors.border}`,
          transition: 'all 0.3s ease',
          '&:hover': {
            borderColor: colors.badge,
            boxShadow: `0 10px 25px ${colors.bg}`,
            transform: 'translateY(-2px)',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ color: colors.text, display: 'flex', alignItems: 'center', fontSize: '1.25rem' }}>
              {icon}
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 600, color: '#f1f5f9', fontSize: '0.875rem' }}>
              {title}
            </Typography>
          </Box>
          <Box
            sx={{
              px: 1.5,
              py: 0.5,
              borderRadius: 2,
              bgcolor: colors.badge,
              color: 'white',
              fontSize: '0.65rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {severity}
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 2, mb: 1 }}>
          <Typography
            variant="h5"
            sx={{ fontWeight: 700, color: colors.text, fontFamily: '"JetBrains Mono", monospace' }}
          >
            {typeof count === 'number' ? count.toLocaleString() : count}
          </Typography>
          <Typography
            variant="body2"
            sx={{ fontWeight: 600, color: '#94a3b8', fontFamily: '"JetBrains Mono", monospace' }}
          >
            {amount}
          </Typography>
        </Box>

        <Typography variant="body2" sx={{ color: '#64748b', fontSize: '0.8rem', lineHeight: 1.5 }}>
          {description}
        </Typography>
      </Box>
    </motion.div>
  );
};

export default EvidenceCard;
