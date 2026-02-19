import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import { Brightness4, Brightness7 } from '@mui/icons-material';
import { motion } from 'framer-motion';

interface ThemeToggleProps {
  mode: 'dark' | 'light';
  onToggle: () => void;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ mode, onToggle }) => {
  return (
    <Tooltip title={`Switch to ${mode === 'dark' ? 'light' : 'dark'} mode`}>
      <IconButton onClick={onToggle} sx={{ ml: 1 }}>
        <motion.div
          initial={{ rotate: 0, scale: 1 }}
          animate={{ rotate: mode === 'dark' ? 0 : 180, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          {mode === 'dark' ? <Brightness7 /> : <Brightness4 />}
        </motion.div>
      </IconButton>
    </Tooltip>
  );
};

export default ThemeToggle;
