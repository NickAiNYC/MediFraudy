import React from 'react';
import { Card, CardContent, Typography, Box, LinearProgress, List, ListItem, ListItemText, ListItemAvatar, Avatar } from '@mui/material';
import LocalPharmacyIcon from '@mui/icons-material/LocalPharmacy';

interface PharmacyMeterProps {
  data: Array<{
    provider_id: number;
    provider_name: string;
    total_cost: number;
    script_count: number;
  }>;
}

export const PharmacyMeter: React.FC<PharmacyMeterProps> = ({ data }) => {
  // Robust guard clause: ensure data is an array
  const safeData = Array.isArray(data) ? data : [];

  if (safeData.length === 0) {
      return (
          <Card sx={{ height: '100%' }}>
              <CardContent>
                  <Typography variant="h6" gutterBottom>Pharmacy Dumping Meter</Typography>
                  <Typography variant="body2" color="textSecondary">
                      No data available or invalid format received.
                  </Typography>
              </CardContent>
          </Card>
      );
  }

  // Safe map with additional check
  const maxCost = Math.max(...safeData.filter(d => d && typeof d.total_cost === 'number').map(d => d.total_cost), 1000);

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Pharmacy Dumping Meter
        </Typography>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          Top Lidocaine offenders by total cost.
        </Typography>
        <List>
          {safeData.map((item) => (
            <ListItem key={item.provider_id}>
              <ListItemAvatar>
                <Avatar sx={{ bgcolor: '#e91e63' }}>
                  <LocalPharmacyIcon />
                </Avatar>
              </ListItemAvatar>
              <ListItemText
                primary={item.provider_name}
                secondary={`$${(item.total_cost || 0).toLocaleString()} (${item.script_count || 0} scripts)`}
              />
              <Box sx={{ width: '40%', mr: 1 }}>
                <LinearProgress 
                    variant="determinate" 
                    value={maxCost > 0 ? ((item.total_cost || 0) / maxCost) * 100 : 0} 
                    color="secondary"
                    sx={{ height: 10, borderRadius: 5 }}
                />
              </Box>
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};
