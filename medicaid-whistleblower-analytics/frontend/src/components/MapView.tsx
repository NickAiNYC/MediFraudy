import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

/**
 * MapView placeholder — requires a map token (e.g. Mapbox) for full
 * geographic rendering. Shows a text-based summary until configured.
 */
const MapView: React.FC = () => (
  <Box>
    <Typography variant="h5" gutterBottom>
      Provider Map (NYC Focus)
    </Typography>
    <Paper sx={{ p: 3, textAlign: 'center' }}>
      <Typography variant="body1" color="text.secondary">
        Geographic visualization requires a MAPBOX_TOKEN in your environment.
      </Typography>
      <Typography variant="body2" sx={{ mt: 1 }}>
        Configure <code>REACT_APP_MAPBOX_TOKEN</code> and install{' '}
        <code>react-map-gl</code> to enable the interactive map.
      </Typography>
    </Paper>
  </Box>
);

export default MapView;
