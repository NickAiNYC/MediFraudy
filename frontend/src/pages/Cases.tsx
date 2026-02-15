import React from 'react';
import { Box } from '@mui/material';
import CaseManager from '../components/CaseManager';

const Cases: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <CaseManager />
    </Box>
  );
};

export default Cases;
