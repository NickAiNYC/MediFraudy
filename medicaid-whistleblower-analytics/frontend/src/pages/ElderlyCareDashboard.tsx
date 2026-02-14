import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  Divider,
  Button,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import { useNavigate } from 'react-router-dom';
import RefreshIcon from '@mui/icons-material/Refresh';
import WarningIcon from '@mui/icons-material/Warning';
import AssessmentIcon from '@mui/icons-material/Assessment';
import DownloadIcon from '@mui/icons-material/Download';

// Import from modular API
import { analyticsApi, polApi, exportApi } from '../services/api';

/** Target billing codes from recent Brooklyn/Queens/Albany prosecutions. */
const TARGET_CODE_GROUPS = {
  'Adult Day Care': ['T2024', 'T2025', 'S5100', 'S5101', 'S5102', 'S5105'],
  'Home Health': ['G0151', 'G0152', 'G0153', 'G0154', 'G0155', 'G0156', 'G0157', 'G0159'],
  'Capacity Related': ['T2024', 'T2025'],
  'Therapy': ['97110', '97530', '97140'],
};

const PIE_COLORS = ['#1976d2', '#d32f2f', '#388e3c', '#f57c00', '#7b1fa2', '#0288d1', '#9c27b0'];

interface SweepResult {
  provider_id: number;
  npi: string;
  name: string;
  city: string;
  facility_type: string;
  risk_score: number;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  findings_count: number;
}

const ElderlyCareDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [patterns, setPatterns] = useState<any[]>([]);
  const [outliers, setOutliers] = useState<any[]>([]);
  const [sweepResults, setSweepResults] = useState<SweepResult[]>([]);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState({
    patterns: false,
    outliers: false,
    sweep: false,
    trends: false,
  });
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setError(null);
    
    // Fetch patterns
    setLoading(prev => ({ ...prev, patterns: true }));
    try {
      const data = await analyticsApi.getFraudPatterns();
      setPatterns(data || []);
    } catch (err: any) {
      console.error('Failed to fetch patterns:', err);
    } finally {
      setLoading(prev => ({ ...prev, patterns: false }));
    }

    // Fetch outliers
    setLoading(prev => ({ ...prev, outliers: true }));
    try {
      const data = await analyticsApi.getOutliers(3, 'NY');
      setOutliers(data || []);
    } catch (err: any) {
      console.error('Failed to fetch outliers:', err);
    } finally {
      setLoading(prev => ({ ...prev, outliers: false }));
    }

    // Fetch NYC sweep (top 20 high-risk facilities)
    setLoading(prev => ({ ...prev, sweep: true }));
    try {
      const data = await polApi.getNYCElderlySweep(50, 20);
      setSweepResults(data.results || []);
    } catch (err: any) {
      console.error('Failed to fetch sweep results:', err);
    } finally {
      setLoading(prev => ({ ...prev, sweep: false }));
    }

    // Fetch trends
    setLoading(prev => ({ ...prev, trends: true }));
    try {
      const data = await analyticsApi.getTrends('NY');
      setTrends(data || []);
    } catch (err: any) {
      console.error('Failed to fetch trends:', err);
    } finally {
      setLoading(prev => ({ ...prev, trends: false }));
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const patternCounts = patterns.reduce<Record<string, number>>((acc, p) => {
    acc[p.pattern] = (acc[p.pattern] || 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(patternCounts).map(([name, value]) => ({ 
    name: name.replace(/_/g, ' '), 
    value 
  }));

  const getRiskColor = (severity: string) => {
    switch(severity) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      default: return 'success';
    }
  };

  const handleViewProvider = (providerId: number) => {
    navigate(`/providers/${providerId}`);
  };

  const handleDownloadReport = (providerId: number, providerName: string) => {
    exportApi.downloadProviderReport(providerId);
  };

  const isLoading = Object.values(loading).some(Boolean);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">
          NYC Elderly Care & Rehabilitation Dashboard
        </Typography>
        <Button 
          variant="outlined" 
          startIcon={<RefreshIcon />} 
          onClick={fetchData}
          disabled={isLoading}
        >
          Refresh
        </Button>
      </Box>

      <Alert severity="warning" sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon />
          <Box>
            <strong>Urgency context:</strong> Queens $120M charges filed Feb 9, 2026 · 
            Brooklyn $68M pleas Jan 2026 · Albany $1.3M settled Feb 11, 2026.
            Dataset released Feb 13, 2026.
          </Box>
        </Box>
      </Alert>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Fraud Patterns Detected
              </Typography>
              <Typography variant="h4">
                {loading.patterns ? <CircularProgress size={24} /> : patterns.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Outlier Providers (Z ≥ 3)
              </Typography>
              <Typography variant="h4">
                {loading.outliers ? <CircularProgress size={24} /> : outliers.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                High-Risk Facilities
              </Typography>
              <Typography variant="h4" color="error">
                {loading.sweep ? <CircularProgress size={24} /> : 
                  sweepResults.filter(r => r.severity === 'HIGH').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Target Code Groups
              </Typography>
              <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {Object.keys(TARGET_CODE_GROUPS).map((g) => (
                  <Chip key={g} label={g} size="small" variant="outlined" />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Divider sx={{ mb: 3 }} />

      {/* High-Risk Facilities Table */}
      <Typography variant="h6" gutterBottom>
        Top High-Risk Facilities in NYC
        {loading.sweep && <LinearProgress sx={{ mt: 1 }} />}
      </Typography>
      
      <TableContainer component={Paper} sx={{ mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell><strong>Facility Name</strong></TableCell>
              <TableCell><strong>Type</strong></TableCell>
              <TableCell><strong>Borough</strong></TableCell>
              <TableCell><strong>Risk Score</strong></TableCell>
              <TableCell><strong>Findings</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sweepResults.map((facility) => (
              <TableRow 
                key={facility.provider_id}
                sx={{ 
                  backgroundColor: facility.severity === 'HIGH' ? '#fff2f0' : 'inherit',
                  '&:hover': { backgroundColor: '#f5f5f5' }
                }}
              >
                <TableCell>{facility.name}</TableCell>
                <TableCell>
                  <Chip 
                    label={facility.facility_type?.replace(/_/g, ' ') || 'Unknown'}
                    size="small"
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>{facility.city}</TableCell>
                <TableCell>
                  <Chip 
                    label={facility.risk_score}
                    color={getRiskColor(facility.severity)}
                    size="small"
                    sx={{ fontWeight: 'bold' }}
                  />
                </TableCell>
                <TableCell>{facility.findings_count}</TableCell>
                <TableCell align="center">
                  <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
                    <Tooltip title="View Pattern-of-Life Analysis">
                      <IconButton 
                        size="small"
                        onClick={() => handleViewProvider(facility.provider_id)}
                        color="primary"
                      >
                        <AssessmentIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Download Report">
                      <IconButton 
                        size="small"
                        onClick={() => handleDownloadReport(facility.provider_id, facility.name)}
                        color="secondary"
                      >
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
            {sweepResults.length === 0 && !loading.sweep && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                  No high-risk facilities found. Try adjusting the risk threshold.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Charts Row */}
      <Grid container spacing={3}>
        {/* Pattern Distribution Pie Chart */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Typography variant="h6" gutterBottom>
            Fraud Pattern Distribution
          </Typography>
          <Paper sx={{ p: 2, height: 300 }}>
            {loading.patterns ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <CircularProgress />
              </Box>
            ) : pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie 
                    data={pieData} 
                    dataKey="value" 
                    nameKey="name" 
                    cx="50%" 
                    cy="50%" 
                    outerRadius={80} 
                    label
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <Typography color="textSecondary">No pattern data available</Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Outliers Bar Chart */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Typography variant="h6" gutterBottom>
            Top Outlier Providers by Z-Score
          </Typography>
          <Paper sx={{ p: 2, height: 300 }}>
            {loading.outliers ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <CircularProgress />
              </Box>
            ) : outliers.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={outliers.slice(0, 10)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="npi" />
                  <YAxis />
                  <RechartsTooltip />
                  <Bar dataKey="z_score" fill="#d32f2f" name="Z-Score" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <Typography color="textSecondary">No outlier data available</Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Year-over-Year Trends */}
        <Grid size={{ xs: 12 }}>
          <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
            Year-over-Year Billing Trends (NY State)
          </Typography>
          <Paper sx={{ p: 2, height: 300 }}>
            {loading.trends ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <CircularProgress />
              </Box>
            ) : trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis />
                  <RechartsTooltip />
                  <Legend />
                  <Line type="monotone" dataKey="total" stroke="#1976d2" name="Total Billing ($)" />
                  <Line type="monotone" dataKey="claim_count" stroke="#d32f2f" name="Claim Count" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <Typography color="textSecondary">No trend data available</Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Data Freshness Note */}
      <Box sx={{ mt: 3, textAlign: 'right' }}>
        <Typography variant="caption" color="textSecondary">
          Data source: HHS DOGE Medicaid dataset (released Feb 13, 2026)
        </Typography>
      </Box>
    </Box>
  );
};

export default ElderlyCareDashboard;
