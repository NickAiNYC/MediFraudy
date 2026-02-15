import React from 'react';
import { Box, Typography } from '@mui/material';
import ProviderSearch from '../components/ProviderSearch';

const Providers: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Provider Search
      </Typography>
      <ProviderSearch />
    </Box>
  );
};

export default Providers;
