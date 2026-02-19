import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  LinearProgress,
  Stack,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  AttachMoney,
  Warning,
  People,
  Assessment,
  Download,
  Refresh,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';

interface MetricCardProps {
  title: string;
  value: number;
  change: number;
  prefix?: string;
  suffix?: string;
  icon: React.ReactNode;
  color: string;
  format?: 'number' | 'currency' | 'percent';
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  prefix = '',
  suffix = '',
  icon,
  color,
  format = 'number',
}) => {
  const isPositive = change > 0;
  const formattedValue = format === 'currency' ? value.toLocaleString() : value;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card
        sx={{
          background: `linear-gradient(135deg, ${color}15 0%, ${color}05 100%)`,
          border: `1px solid ${color}40`,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
            <Box>
              <Typography variant="caption" sx={{ color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                {title}
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, mt: 1, color: color }}>
                {prefix}
                <CountUp end={formattedValue as number} duration={2} separator="," />
                {suffix}
              </Typography>
            </Box>
            <Box
              sx={{
                bgcolor: `${color}20`,
                p: 1.5,
                borderRadius: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {icon}
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              icon={isPositive ? <TrendingUp sx={{ fontSize: 14 }} /> : <TrendingDown sx={{ fontSize: 14 }} />}
              label={`${isPositive ? '+' : ''}${change}%`}
              size="small"
              sx={{
                bgcolor: isPositive ? '#10b98120' : '#ef444420',
                color: isPositive ? '#10b981' : '#ef4444',
                fontWeight: 700,
                fontSize: '0.7rem',
                '& .MuiChip-icon': {
                  color: isPositive ? '#10b981' : '#ef4444',
                },
              }}
            />
            <Typography variant="caption" sx={{ color: '#64748b' }}>
              vs last month
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export const ExecutiveSummary: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/data-loading/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    fetchStats();
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const trendData = stats?.trend_data || [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
            Executive Summary
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748b' }}>
            Real-time fraud intelligence overview • Last updated: {new Date().toLocaleTimeString()}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Tooltip title="Refresh data">
            <IconButton onClick={handleRefresh} size="small" disabled={loading}>
              <Refresh sx={{ fontSize: 20 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title="Export PDF report">
            <IconButton size="small">
              <Download sx={{ fontSize: 20 }} />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2, borderRadius: 2 }} />}

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <MetricCard
            title="Total Claims"
            value={stats?.claims?.total || 0}
            change={0}
            icon={<AttachMoney sx={{ color: '#ef4444', fontSize: 28 }} />}
            color="#ef4444"
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <MetricCard
            title="Total Providers"
            value={stats?.providers?.total || 0}
            change={0}
            icon={<Warning sx={{ color: '#f59e0b', fontSize: 28 }} />}
            color="#f59e0b"
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <MetricCard
            title="NYC Providers"
            value={stats?.providers?.nyc || 0}
            change={0}
            icon={<Assessment sx={{ color: '#3b82f6', fontSize: 28 }} />}
            color="#3b82f6"
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <MetricCard
            title="Providers with Claims"
            value={stats?.data_quality?.providers_with_claims || 0}
            change={0}
            icon={<People sx={{ color: '#10b981', fontSize: 28 }} />}
            color="#10b981"
          />
        </Grid>

        <Grid item xs={12} md={8}>
          <Card sx={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', border: '1px solid #334155' }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>
                Fraud Detection Trend
              </Typography>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="fraudGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="month" stroke="#64748b" style={{ fontSize: '0.75rem' }} />
                  <YAxis stroke="#64748b" style={{ fontSize: '0.75rem' }} />
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      border: '1px solid #334155',
                      borderRadius: 8,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="fraud"
                    stroke="#ef4444"
                    strokeWidth={3}
                    fill="url(#fraudGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card sx={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', border: '1px solid #334155', height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>
                Top Fraud Categories
              </Typography>
              <Stack spacing={2}>
                {[
                  { name: 'Billing Inflation', value: 34, color: '#ef4444' },
                  { name: 'Ghost Billing', value: 28, color: '#f59e0b' },
                  { name: 'Kickback Schemes', value: 22, color: '#3b82f6' },
                  { name: 'Capacity Violations', value: 16, color: '#8b5cf6' },
                ].map((category) => (
                  <Box key={category.name}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {category.name}
                      </Typography>
                      <Typography variant="body2" sx={{ color: category.color, fontWeight: 700 }}>
                        {category.value}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={category.value}
                      sx={{
                        height: 8,
                        borderRadius: 4,
                        bgcolor: '#1e293b',
                        '& .MuiLinearProgress-bar': {
                          bgcolor: category.color,
                          borderRadius: 4,
                        },
                      }}
                    />
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ExecutiveSummary;
