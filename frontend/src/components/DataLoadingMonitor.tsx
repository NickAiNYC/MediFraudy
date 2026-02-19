import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  Stack,
  IconButton,
  Tooltip,
  Alert,
} from '@mui/material';
import {
  CloudUpload,
  CheckCircle,
  Error,
  Refresh,
  Speed,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';

interface LoadingProgress {
  status: string;
  rows_loaded: number;
  last_checkpoint: number;
  updated_at: string;
  file_size_gb: number;
}

export const DataLoadingMonitor: React.FC = () => {
  const [progress, setProgress] = useState<LoadingProgress | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchProgress = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/data-loading/progress');
      if (response.ok) {
        const data = await response.json();
        setProgress(data);
      } else if (response.status === 404) {
        // No loading in progress
        setProgress(null);
      }
    } catch (error) {
      console.error('Failed to fetch progress:', error);
      setProgress(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProgress();
    const interval = setInterval(fetchProgress, 10000); // Update every 10s
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'loading': return '#3b82f6';
      case 'failed': return '#ef4444';
      default: return '#64748b';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle />;
      case 'loading': return <CloudUpload />;
      case 'failed': return <Error />;
      default: return <Speed />;
    }
  };

  if (!progress || progress.status === 'not_started') {
    return null;
  }

  const progressPercent = progress.rows_loaded ? (progress.rows_loaded / 77300000) * 100 : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card
        sx={{
          background: 'linear-gradient(135deg, #3b82f615 0%, #3b82f605 100%)',
          border: '1px solid #3b82f640',
          mb: 3,
        }}
      >
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box
                sx={{
                  bgcolor: `${getStatusColor(progress.status)}20`,
                  p: 1.5,
                  borderRadius: 2,
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {getStatusIcon(progress.status)}
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Data Loading Progress
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748b' }}>
                  {progress.file_size_gb}GB file • Last updated: {new Date(progress.updated_at).toLocaleTimeString()}
                </Typography>
              </Box>
            </Box>
            <Stack direction="row" spacing={1} alignItems="center">
              <Chip
                label={progress.status.toUpperCase()}
                size="small"
                sx={{
                  bgcolor: getStatusColor(progress.status),
                  color: 'white',
                  fontWeight: 700,
                  fontSize: '0.7rem',
                }}
              />
              <Tooltip title="Refresh">
                <IconButton onClick={fetchProgress} size="small" disabled={loading}>
                  <Refresh sx={{ fontSize: 20 }} />
                </IconButton>
              </Tooltip>
            </Stack>
          </Box>

          {progress.status === 'loading' && (
            <>
              <LinearProgress
                variant="determinate"
                value={progressPercent}
                sx={{
                  height: 12,
                  borderRadius: 6,
                  bgcolor: '#1e293b',
                  mb: 2,
                  '& .MuiLinearProgress-bar': {
                    bgcolor: '#3b82f6',
                    borderRadius: 6,
                  },
                }}
              />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  <CountUp end={progress.rows_loaded} duration={1} separator="," /> / 77,300,000 rows
                </Typography>
                <Typography variant="body2" sx={{ color: '#3b82f6', fontWeight: 700 }}>
                  {progressPercent.toFixed(1)}%
                </Typography>
              </Box>
            </>
          )}

          {progress.status === 'completed' && (
            <Alert severity="success" sx={{ bgcolor: '#10b98120', border: '1px solid #10b98140' }}>
              Data loading complete! {progress.rows_loaded.toLocaleString()} rows loaded successfully.
            </Alert>
          )}

          {progress.status === 'failed' && (
            <Alert severity="error" sx={{ bgcolor: '#ef444420', border: '1px solid #ef444440' }}>
              Data loading failed. Check logs or resume from checkpoint.
            </Alert>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default DataLoadingMonitor;
