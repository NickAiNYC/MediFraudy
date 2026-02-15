import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { Gavel as GavelIcon } from '@mui/icons-material';
import { motion } from 'framer-motion';
import CaseManager from '../components/CaseManager';

const Cases: React.FC = () => {
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
            Case Management
          </Typography>
          <Chip
            icon={<GavelIcon sx={{ fontSize: '0.85rem' }} />}
            label="FCA Litigation"
            size="small"
            sx={{
              bgcolor: 'rgba(239, 68, 68, 0.1)',
              color: '#f87171',
              fontWeight: 600,
              fontSize: '0.7rem',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              '& .MuiChip-icon': { color: '#f87171' },
            }}
          />
        </Box>
        <Typography variant="body2" sx={{ color: '#64748b', mb: 3 }}>
          Manage whistleblower cases and False Claims Act litigation tracking
        </Typography>
      </motion.div>
      <CaseManager />
    </Box>
  );
};

export default Cases;
