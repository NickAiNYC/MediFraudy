import React from 'react';
import { Card, CardContent, Typography, Box, Chip } from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';

interface RiskScoreCardProps {
  score: number;
  breakdown: {
    sadc: number;
    cdpap: number;
    pharmacy: number;
    recipient?: number;
  };
}

export const RiskScoreCard: React.FC<RiskScoreCardProps> = ({ score, breakdown }) => {
  let color = 'success.main';
  if (score > 50) color = 'warning.main';
  if (score > 80) color = 'error.main';

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Priority Risk Score
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <WarningIcon sx={{ fontSize: 40, color: color, mr: 2 }} />
            <Typography variant="h3" color={color}>
                {score}
            </Typography>
            <Typography variant="caption" sx={{ ml: 1, mt: 2 }}>
                / 100
            </Typography>
        </Box>
        <Typography variant="subtitle2" gutterBottom>
            Vector Breakdown:
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip label={`SADC: ${breakdown.sadc}`} color={breakdown.sadc > 0 ? "error" : "default"} />
            <Chip label={`CDPAP: ${breakdown.cdpap}`} color={breakdown.cdpap > 0 ? "warning" : "default"} />
            <Chip label={`RX: ${breakdown.pharmacy}`} color={breakdown.pharmacy > 0 ? "secondary" : "default"} />
            {breakdown.recipient !== undefined && (
                <Chip label={`Users: ${breakdown.recipient}`} color={breakdown.recipient > 0 ? "primary" : "default"} />
            )}
        </Box>
      </CardContent>
    </Card>
  );
};
