import React from 'react';
import { Box, Typography } from '@mui/material';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';

interface StatCardProps {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  separator?: string;
  duration?: number;
  icon: React.ReactNode;
  trend?: string;
  trendIcon?: React.ReactNode;
  delay?: number;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  prefix = '',
  suffix = '',
  decimals = 0,
  separator = ',',
  duration = 2,
  icon,
  trend,
  trendIcon,
  delay = 0,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      <Box
        sx={{
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          borderRadius: 3,
          p: 3,
          border: '1px solid #334155',
          transition: 'all 0.3s ease',
          '&:hover': {
            borderColor: '#10b981',
            boxShadow: '0 20px 25px rgba(16, 185, 129, 0.1)',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography
            variant="body2"
            sx={{
              color: '#94a3b8',
              fontSize: '0.75rem',
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {title}
          </Typography>
          <Box sx={{ color: '#10b981', display: 'flex', alignItems: 'center' }}>
            {icon}
          </Box>
        </Box>
        <Typography
          variant="h4"
          sx={{
            fontWeight: 700,
            color: '#f1f5f9',
            mb: 0.5,
            fontFamily: '"JetBrains Mono", monospace',
          }}
        >
          {prefix}
          <CountUp end={value} duration={duration} separator={separator} decimals={decimals} />
          {suffix}
        </Typography>
        {trend && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {trendIcon && (
              <Box sx={{ color: '#10b981', display: 'flex', alignItems: 'center', fontSize: '1rem' }}>
                {trendIcon}
              </Box>
            )}
            <Typography
              variant="body2"
              sx={{ color: '#10b981', fontWeight: 500, fontSize: '0.8rem' }}
            >
              {trend}
            </Typography>
          </Box>
        )}
      </Box>
    </motion.div>
  );
};

export default StatCard;
