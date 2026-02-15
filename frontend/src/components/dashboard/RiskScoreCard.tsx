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
    nemt?: number;
  };
}

export const RiskScoreCard: React.FC<RiskScoreCardProps> = ({ score, breakdown }) => {
  const scoreColor = score > 80 ? '#ef4444' : score > 50 ? '#f59e0b' : '#10b981';

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ color: '#f1f5f9', fontWeight: 600 }}>
          Priority Risk Score
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <WarningIcon sx={{ fontSize: 40, color: scoreColor, mr: 2 }} />
            <Typography variant="h3" sx={{ color: scoreColor, fontWeight: 800, fontFamily: '"JetBrains Mono", monospace' }}>
                {score}
            </Typography>
            <Typography variant="caption" sx={{ ml: 1, mt: 2, color: '#64748b' }}>
                / 100
            </Typography>
        </Box>
        <Typography variant="subtitle2" gutterBottom sx={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Vector Breakdown:
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              label={`SADC: ${breakdown.sadc}`}
              size="small"
              sx={{
                bgcolor: breakdown.sadc > 0 ? 'rgba(239,68,68,0.15)' : 'rgba(148,163,184,0.1)',
                color: breakdown.sadc > 0 ? '#f87171' : '#64748b',
                fontWeight: 600,
                fontSize: '0.7rem',
                fontFamily: '"JetBrains Mono", monospace',
              }}
            />
            <Chip
              label={`CDPAP: ${breakdown.cdpap}`}
              size="small"
              sx={{
                bgcolor: breakdown.cdpap > 0 ? 'rgba(249,115,22,0.15)' : 'rgba(148,163,184,0.1)',
                color: breakdown.cdpap > 0 ? '#fb923c' : '#64748b',
                fontWeight: 600,
                fontSize: '0.7rem',
                fontFamily: '"JetBrains Mono", monospace',
              }}
            />
            <Chip
              label={`RX: ${breakdown.pharmacy}`}
              size="small"
              sx={{
                bgcolor: breakdown.pharmacy > 0 ? 'rgba(168,85,247,0.15)' : 'rgba(148,163,184,0.1)',
                color: breakdown.pharmacy > 0 ? '#c084fc' : '#64748b',
                fontWeight: 600,
                fontSize: '0.7rem',
                fontFamily: '"JetBrains Mono", monospace',
              }}
            />
            {breakdown.recipient !== undefined && (
                <Chip
                  label={`Users: ${breakdown.recipient}`}
                  size="small"
                  sx={{
                    bgcolor: breakdown.recipient > 0 ? 'rgba(59,130,246,0.15)' : 'rgba(148,163,184,0.1)',
                    color: breakdown.recipient > 0 ? '#60a5fa' : '#64748b',
                    fontWeight: 600,
                    fontSize: '0.7rem',
                    fontFamily: '"JetBrains Mono", monospace',
                  }}
                />
            )}
            {breakdown.nemt !== undefined && breakdown.nemt > 0 && (
                <Chip
                  label={`NEMT: ${breakdown.nemt}`}
                  size="small"
                  sx={{
                    bgcolor: 'rgba(245,158,11,0.15)',
                    color: '#fbbf24',
                    fontWeight: 600,
                    fontSize: '0.7rem',
                    fontFamily: '"JetBrains Mono", monospace',
                  }}
                />
            )}
        </Box>
      </CardContent>
    </Card>
  );
};
