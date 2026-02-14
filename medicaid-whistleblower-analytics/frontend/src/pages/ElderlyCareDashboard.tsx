import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  Divider,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { getFraudPatterns, getOutliers } from '../services/api';

/** Target billing codes from recent Brooklyn/Queens/Albany prosecutions. */
const TARGET_CODE_GROUPS = {
  'Adult Day Care': ['T2024', 'T2025', 'S5100', 'S5101', 'S5102', 'S5105'],
  'Home Health': ['G0151', 'G0152', 'G0153', 'G0154', 'G0155', 'G0156', 'G0157', 'G0159'],
  'Capacity Related': ['T2024', 'T2025'],
};

const PIE_COLORS = ['#1976d2', '#d32f2f', '#388e3c', '#f57c00', '#7b1fa2'];

const ElderlyCareDashboard: React.FC = () => {
  const [patterns, setPatterns] = useState<any[]>([]);
  const [outliers, setOutliers] = useState<any[]>([]);

  useEffect(() => {
    getFraudPatterns().then(({ data }) => setPatterns(data)).catch(console.error);
    getOutliers(3, 'NY').then(({ data }) => setOutliers(data)).catch(console.error);
  }, []);

  const patternCounts = patterns.reduce<Record<string, number>>((acc, p) => {
    acc[p.pattern] = (acc[p.pattern] || 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(patternCounts).map(([name, value]) => ({ name, value }));

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Elderly Care &amp; Rehabilitation Dashboard
      </Typography>

      <Alert severity="warning" sx={{ mb: 2 }}>
        <strong>Urgency context:</strong> Queens $120M charges filed Feb 9, 2026 &middot;
        Brooklyn $68M pleas Jan 2026 &middot; Albany $1.3M settled Feb 11, 2026.
        Dataset released Feb 13, 2026.
      </Alert>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Fraud Patterns Detected
              </Typography>
              <Typography variant="h4">{patterns.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Outlier Providers (Z &ge; 3)
              </Typography>
              <Typography variant="h4">{outliers.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Target Code Groups
              </Typography>
              <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {Object.keys(TARGET_CODE_GROUPS).map((g) => (
                  <Chip key={g} label={g} size="small" />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Divider sx={{ mb: 2 }} />

      {/* Pattern Distribution */}
      <Typography variant="h6" gutterBottom>
        Fraud Pattern Distribution
      </Typography>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
            {pieData.map((_, i) => (
              <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>

      {/* Outlier Bar Chart */}
      <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
        Top Outlier Providers by Z-Score
      </Typography>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={outliers.slice(0, 15)}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="npi" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="z_score" fill="#d32f2f" name="Z-Score" />
        </BarChart>
      </ResponsiveContainer>

      {/* Capacity Violation Placeholder */}
      <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
        Capacity Heatmap (Billing vs Licensed Capacity)
      </Typography>
      <Card>
        <CardContent>
          <Typography color="text.secondary">
            Load the full dataset to populate this visualization. Detects facilities billing
            more patients than their licensed capacity — the pattern from the Queens $120M case.
          </Typography>
        </CardContent>
      </Card>

      {/* Referral Network Placeholder */}
      <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
        Physician Referral Network
      </Typography>
      <Card>
        <CardContent>
          <Typography color="text.secondary">
            Network graph shows referring physician relationships to flag potential kickback
            schemes — the pattern from the Brooklyn $68M case.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ElderlyCareDashboard;
