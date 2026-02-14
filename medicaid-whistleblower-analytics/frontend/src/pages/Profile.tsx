import React from 'react';
import { Typography, Box, Paper } from '@mui/material';

const Profile: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        User Profile
      </Typography>
      <Paper sx={{ p: 3 }}>
        <Typography>Profile settings coming soon...</Typography>
      </Paper>
    </Box>
  );
};

export default Profile;
