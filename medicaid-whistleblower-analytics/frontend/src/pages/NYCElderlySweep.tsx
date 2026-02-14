import React from 'react';
import { Typography, Box, Paper } from '@mui/material';

const NYCElderlySweep: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        NYC Elderly Care Sweep
      </Typography>
      <Paper sx={{ p: 3 }}>
        <Typography>NYC elderly care facilities analysis coming soon...</Typography>
      </Paper>
    </Box>
  );
};

export default NYCElderlySweep;
