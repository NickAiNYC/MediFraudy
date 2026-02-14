import React from 'react';
import { Typography, Box, Paper } from '@mui/material';

const PatternOfLife: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Pattern-of-Life Analysis
      </Typography>
      <Paper sx={{ p: 3 }}>
        <Typography>Pattern-of-life forensic analysis coming soon...</Typography>
      </Paper>
    </Box>
  );
};

export default PatternOfLife;
