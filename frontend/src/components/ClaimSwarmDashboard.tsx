import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  Alert,
  Button,
  Tabs,
  Tab,
  CircularProgress,
  IconButton,
  Tooltip,
  Badge,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Security,
  Warning,
  CheckCircle,
  Error,
  Info,
  Timeline,
  TimelineDot,
  TimelineItem,
  TimelineSeparator,
  TimelineContent,
  TimelineOppositeContent,
  TimelineConnector,
  Assessment,
  Speed,
  Verified,
  Gavel,
  AccountBalance,
  NetworkCheck,
  Group
} from '@mui/icons-material';
import { LineChart, LineChartProps } from 'recharts';
import { BarChart, BarChartProps } from 'recharts';
import { PieChart, PieChartProps } from 'recharts';
import { XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';

interface ClaimMetrics {
  total_claims: number;
  approved_claims: number;
  escalated_claims: number;
  approval_rate: number;
  complexity_breakdown: {
    simple: number;
    moderate: number;
    complex: number;
    critical: number;
  };
  avg_fraud_score: number;
  avg_processing_time: number;
  total_estimated_cost: number;
}

interface FraudGraphMetrics {
  total_entities: number;
  total_connections: number;
  high_risk_entities: number;
  connected_components: number;
  average_clustering: number;
}

interface Claim {
  claim_id: string;
  complexity: string;
  status: string;
  fraud_score: number;
  estimated_cost: number;
  confidence: number;
  recommendation: string;
  processing_time: number;
  blockchain_hash: string;
  created_at: string;
}

const ClaimSwarmDashboard: React.FC = () => {
  const [claimMetrics, setClaimMetrics] = useState<ClaimMetrics>({
    total_claims: 0,
    approved_claims: 0,
    escalated_claims: 0,
    approval_rate: 0,
    complexity_breakdown: {
      simple: 0,
      moderate: 0,
      complex: 0,
      critical: 0
    },
    avg_fraud_score: 0,
    avg_processing_time: 0,
    total_estimated_cost: 0
  });

  const [fraudGraphMetrics, setFraudGraphMetrics] = useState<FraudGraphMetrics>({
    total_entities: 0,
    total_connections: 0,
    high_risk_entities: 0,
    connected_components: 0,
    average_clustering: 0
  });

  const [recentClaims, setRecentClaims] = useState<Claim[]>([]);
  const [selectedTab, setSelectedTab] = useState(0);

  // Mock data for demonstration
  useEffect(() => {
    // Simulate real-time updates
    const interval = setInterval(() => {
      setClaimMetrics(prev => ({
        ...prev,
        total_claims: prev.total_claims + Math.floor(Math.random() * 3),
        approved_claims: prev.approved_claims + Math.floor(Math.random() * 2),
        escalated_claims: prev.escalated_claims + Math.floor(Math.random() * 1),
        total_estimated_cost: prev.total_estimated_cost + Math.random() * 10000
      }));

      setFraudGraphMetrics(prev => ({
        ...prev,
        total_entities: prev.total_entities + Math.floor(Math.random() * 5),
        total_connections: prev.total_connections + Math.floor(Math.random() * 8)
      }));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'simple': return '#4caf50';
      case 'moderate': return '#ff9800';
      case 'complex': return '#f57c00';
      case 'critical': return '#f44336';
      default: return '#9e9e9e';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return '#4caf50';
      case 'escalated': return '#ff9800';
      case 'investigating': return '#2196f3';
      case 'rejected': return '#f44336';
      default: return '#9e9e9e';
    }
  };

  const getFraudScoreColor = (score: number) => {
    if (score >= 0.7) return '#f44336';
    if (score >= 0.5) return '#ff9800';
    if (score >= 0.3) return '#ffeb3b';
    return '#4caf50';
  };

  const renderClaimOverview = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} md={3}>
        <Card sx={{ background: 'linear-gradient(135deg, #4caf50 0%, #66bb6a 100%)', color: 'white' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Total Claims
            </Typography>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h4" fontWeight="bold">
                {claimMetrics.total_claims}
              </Typography>
              <Chip label="Today" size="small" sx={{ ml: 1 }} />
            </Box>
            <Typography variant="body2" color="white">
              +{Math.floor(Math.random() * 10)}% from yesterday
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={3}>
        <Card sx={{ background: 'linear-gradient(135deg, #2196f3 0%, #42a5f5 100%)', color: 'white' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Approval Rate
            </Typography>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h4" fontWeight="bold">
                {claimMetrics.approval_rate.toFixed(1)}%
              </Typography>
              <Chip label="Auto" size="small" sx={{ ml: 1 }} />
            </Box>
            <Typography variant="body2" color="white">
              {claimMetrics.approved_claims} approved
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={3}>
        <Card sx={{ background: 'linear-gradient(135deg, #ff9800 0%, #ffa726 100%)', color: 'white' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Avg Fraud Score
            </Typography>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h4" fontWeight="bold">
                {(claimMetrics.avg_fraud_score * 100).toFixed(1)}%
              </Typography>
              <Chip label="Risk" size="small" sx={{ ml: 1 }} />
            </Box>
            <Typography variant="body2" color="white">
              {claimMetrics.escalated_claims} escalated
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={3}>
        <Card sx={{ background: 'linear-gradient(135deg, #9c27b0 0%, #ab47bc 100%)', color: 'white' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Processing Speed
            </Typography>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h4" fontWeight="bold">
                {claimMetrics.avg_processing_time.toFixed(1)}s
              </Typography>
              <Chip label="Fast" size="small" sx={{ ml: 1 }} />
            </Box>
            <Typography variant="body2" color="white">
              Industry avg: 45s
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderComplexityAnalysis = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} md={8}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Claim Complexity Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart data={[
                { name: 'Simple', value: claimMetrics.complexity_breakdown.simple, fill: '#4caf50' },
                { name: 'Moderate', value: claimMetrics.complexity_breakdown.moderate, fill: '#ff9800' },
                { name: 'Complex', value: claimMetrics.complexity_breakdown.complex, fill: '#f57c00' },
                { name: 'Critical', value: claimMetrics.complexity_breakdown.critical, fill: '#f44336' }
              ]}>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Complexity Breakdown
            </Typography>
            <Box display="flex" flexDirection="column" gap={2}>
              {Object.entries(claimMetrics.complexity_breakdown).map(([complexity, count]) => (
                <Box key={complexity}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                      {complexity}
                    </Typography>
                    <Typography variant="h6" fontWeight="bold">
                      {count}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(count / claimMetrics.total_claims) * 100}
                    sx={{
                      backgroundColor: '#e0e0e0',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: getComplexityColor(complexity)
                      }
                    }}
                  />
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderFraudGraph = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Fraud Graph Metrics
            </Typography>
            <Box display="flex" flexDirection="column" gap={2}>
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2">Total Entities</Typography>
                <Typography variant="h6" fontWeight="bold">{fraudGraphMetrics.total_entities}</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2">Total Connections</Typography>
                <Typography variant="h6" fontWeight="bold">{fraudGraphMetrics.total_connections}</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2">High-Risk Entities</Typography>
                <Typography variant="h6" fontWeight="bold" color="error">{fraudGraphMetrics.high_risk_entities}</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2">Connected Components</Typography>
                <Typography variant="h6" fontWeight="bold">{fraudGraphMetrics.connected_components}</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2">Avg Clustering</Typography>
                <Typography variant="h6" fontWeight="bold">{fraudGraphMetrics.average_clustering.toFixed(3)}</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Fraud Detection Performance
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={[
                { hour: '00:00', detected: 12, prevented: 8 },
                { hour: '04:00', detected: 8, prevented: 6 },
                { hour: '08:00', detected: 15, prevented: 12 },
                { hour: '12:00', detected: 18, prevented: 15 },
                { hour: '16:00', detected: 22, prevented: 18 },
                { hour: '20:00', detected: 14, prevented: 11 }
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="detected" stroke="#ff6b6b" strokeWidth={2} />
                <Line type="monotone" dataKey="prevented" stroke="#4caf50" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderRecentClaims = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Recent Claims Processing
            </Typography>
            <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
              <Table stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Claim ID</TableCell>
                    <TableCell>Complexity</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Fraud Score</TableCell>
                    <TableCell>Est. Cost</TableCell>
                    <TableCell>Processing Time</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {[
                    {
                      claim_id: 'CLM-001',
                      complexity: 'simple',
                      status: 'approved',
                      fraud_score: 0.15,
                      estimated_cost: 2500,
                      processing_time: 2.3
                    },
                    {
                      claim_id: 'CLM-002',
                      complexity: 'moderate',
                      status: 'approved',
                      fraud_score: 0.35,
                      estimated_cost: 8500,
                      processing_time: 4.1
                    },
                    {
                      claim_id: 'CLM-003',
                      complexity: 'complex',
                      status: 'escalated',
                      fraud_score: 0.78,
                      estimated_cost: 15000,
                      processing_time: 8.7
                    },
                    {
                      claim_id: 'CLM-004',
                      complexity: 'critical',
                      status: 'escalated',
                      fraud_score: 0.92,
                      estimated_cost: 45000,
                      processing_time: 12.4
                    }
                  ].map((claim) => (
                    <TableRow key={claim.claim_id}>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {claim.claim_id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={claim.complexity}
                          size="small"
                          sx={{
                            backgroundColor: getComplexityColor(claim.complexity),
                            color: 'white',
                            fontWeight: 'bold'
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={claim.status}
                          size="small"
                          sx={{
                            backgroundColor: getStatusColor(claim.status),
                            color: 'white',
                            fontWeight: 'bold'
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{ color: getFraudScoreColor(claim.fraud_score) }}
                        >
                          {(claim.fraud_score * 100).toFixed(1)}%
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          ${claim.estimated_cost.toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {claim.processing_time}s
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <IconButton size="small">
                          <Info />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderAgentStatus = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={2}>
              <Assessment sx={{ mr: 2, color: '#4caf50' }} />
              <Typography variant="h6">Triage Agent</Typography>
            </Box>
            <LinearProgress variant="determinate" value={95} sx={{ mb: 1 }} />
            <Typography variant="body2" color="textSecondary">
              Operational - 95% accuracy
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={2}>
              <Group sx={{ mr: 2, color: '#2196f3' }} />
              <Typography variant="h6">Investigator Swarm</Typography>
            </Box>
            <LinearProgress variant="determinate" value={88} sx={{ mb: 1 }} />
            <Typography variant="body2" color="textSecondary">
              6 agents active - 88% efficiency
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={2}>
              <Speed sx={{ mr: 2, color: '#ff9800' }} />
              <Typography variant="h6">Estimator Agent</Typography>
            </Box>
            <LinearProgress variant="determinate" value={92} sx={{ mb: 1 }} />
            <Typography variant="body2" color="textSecondary">
              CV models loaded - 92% accuracy
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={2}>
              <Gavel sx={{ mr: 2, color: '#9c27b0' }} />
              <Typography variant="h6">Settler Agent</Typography>
            </Box>
            <LinearProgress variant="determinate" value={97} sx={{ mb: 1 }} />
            <Typography variant="body2" color="textSecondary">
              Auto-approval ready - 97% confidence
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  return (
    <Box sx={{ 
      flexGrow: 1, 
      p: 3, 
      backgroundColor: '#f5f5f5',
      minHeight: '100vh'
    }}>
      <Typography variant="h3" gutterBottom={3} fontWeight="bold">
        🐝 ClaimSwarm Dashboard
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          Autonomous claims processing and fraud detection powered by AI swarm intelligence.
          Processing {claimMetrics.total_claims} claims with {claimMetrics.approval_rate.toFixed(1)}% auto-approval rate.
        </Typography>
      </Alert>
      
      <Box sx={{ mb: 3 }}>
        <Tabs value={selectedTab} onChange={(e, newValue) => setSelectedTab(newValue)}>
          <Tab label="Claim Overview" />
          <Tab label="Complexity Analysis" />
          <Tab label="Fraud Graph" />
          <Tab label="Recent Claims" />
          <Tab label="Agent Status" />
        </Tabs>
      </Box>
      
      {selectedTab === 0 && renderClaimOverview()}
      {selectedTab === 1 && renderComplexityAnalysis()}
      {selectedTab === 2 && renderFraudGraph()}
      {selectedTab === 3 && renderRecentClaims()}
      {selectedTab === 4 && renderAgentStatus()}
    </Box>
  );
};

export default ClaimSwarmDashboard;
