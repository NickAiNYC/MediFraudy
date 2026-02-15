import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { Shield as ShieldIcon } from '@mui/icons-material';
import { motion } from 'framer-motion';
import ProviderSearch from '../components/ProviderSearch';

const Providers: React.FC = () => {
  return (
    <Box>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Typography
            variant="h4"
            sx={{
              fontWeight: 800,
              background: 'linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.025em',
            }}
          >
            Provider Intelligence
          </Typography>
          <Chip
            icon={<ShieldIcon sx={{ fontSize: '0.85rem' }} />}
            label="NYC Focus"
            size="small"
            sx={{
              bgcolor: 'rgba(16, 185, 129, 0.1)',
              color: '#10b981',
              fontWeight: 600,
              fontSize: '0.7rem',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              '& .MuiChip-icon': { color: '#10b981' },
            }}
          />
        </Box>
        <Typography variant="body2" sx={{ color: '#64748b', mb: 3 }}>
          Search, analyze, and investigate Medicaid providers across New York
        </Typography>
      </motion.div>
      <ProviderSearch />
    </Box>
  );
};

export default Providers;
