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
  ListItemIcon
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
  TimelineConnector
} from '@mui/icons-material';
import { LineChart, LineChartProps } from 'recharts';
import { BarChart, BarChartProps } from 'recharts';
import { PieChart, PieChartProps } from 'recharts';
import { XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';

interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'critical';
  aiEngine: {
    status: string;
    predictions_today: number;
    avg_confidence: number;
    model_version: string;
  };
  blockchain: {
    status: string;
    total_blocks: number;
    integrity: string;
    last_block: string;
  };
  monitoring: {
    active_monitors: number;
    alerts_today: number;
    websocket_connections: number;
  };
}

interface Alert {
  alert_id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
  provider_name: string;
  action_required: string;
}

interface Prediction {
  fraud_probability: number;
  corruption_probability: number;
  confidence: number;
  risk_factors: string[];
  timestamp: string;
}

interface BlockchainEvidence {
  total_entries: number;
  integrity_score: number;
  chain_integrity: boolean;
  verification_status: string;
}

const EliteDashboard: React.FC = () => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    overall: 'healthy',
    aiEngine: {
      status: 'healthy',
      predictions_today: 156,
      avg_confidence: 0.87,
      model_version: '2.0.2026'
    },
    blockchain: {
      status: 'healthy',
      total_blocks: 1247,
      integrity: 'verified',
      last_block: '2026-02-19T12:15:30.000Z'
    },
    monitoring: {
      active_monitors: 12,
      alerts_today: 8,
      websocket_connections: 3
    }
  });

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [blockchainEvidence, setBlockchainEvidence] = useState<BlockchainEvidence>({
    total_entries: 1247,
    integrity_score: 0.98,
    chain_integrity: true,
    verification_status: 'verified'
  });

  const [selectedTab, setSelectedTab] = useState(0);

  // Mock data for demonstration
  useEffect(() => {
    // Simulate real-time updates
    const interval = setInterval(() => {
      // Update predictions
      setPredictions(prev => [
        {
          fraud_probability: Math.random() * 0.3,
          corruption_probability: Math.random() * 0.2,
          confidence: 0.85 + Math.random() * 0.15,
          risk_factors: ['High claim frequency', 'Unusual billing patterns'],
          timestamp: new Date().toISOString()
        },
        ...prev.slice(0, 4)
      ]);

      // Update blockchain evidence
      setBlockchainEvidence(prev => ({
        ...prev,
        integrity_score: 0.95 + Math.random() * 0.05,
        total_entries: prev.total_entries + Math.floor(Math.random() * 3)
      }));

      // Update system health
      setSystemHealth(prev => ({
        ...prev,
        aiEngine: {
          ...prev.aiEngine,
          predictions_today: prev.aiEngine.predictions_today + Math.floor(Math.random() * 5)
        },
        blockchain: {
          ...prev.blockchain,
          total_blocks: prev.blockchain.total_blocks + Math.floor(Math.random() * 2)
        }
      }));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#d32f2f';
      case 'high': return '#f57c00';
      case 'medium': return '#ff9800';
      case 'low': return '#4caf50';
      default: return '#9e9e9e';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <Error />;
      case 'high': return <Warning />;
      case 'medium': return <Info />;
      case 'low': return <CheckCircle />;
      default: return <Info />;
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 0.8) return '#d32f2f';
    if (score >= 0.6) return '#f57c00';
    if (score >= 0.4) return '#ff9800';
    return '#4caf50';
  };

  const renderSystemHealth = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              System Health
            </Typography>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h4" fontWeight="bold">
                {systemHealth.overall.toUpperCase()}
              </Typography>
              <Chip 
                label={systemHealth.overall} 
                color={systemHealth.overall === 'healthy' ? 'success' : 'warning'}
                size="small"
                sx={{ ml: 1 }}
              />
            </Box>
            <Typography variant="body2" color="white">
              Last check: {format(new Date(), 'MMM dd, HH:mm:ss')}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card sx={{ background: 'linear-gradient(135deg, #2196f3 0%, #37474f 100%)', color: 'white' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              AI Engine Status
            </Typography>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h4" fontWeight="bold">
                {systemHealth.aiEngine.status.toUpperCase()}
              </Typography>
              <Chip 
                label={`v${systemHealth.aiEngine.model_version}`}
                color="primary"
                size="small"
                sx={{ ml: 1 }}
              />
            </Box>
            <Box display="flex" justifyContent="space-between" mb={2}>
              <Typography variant="body2">Predictions Today</Typography>
              <Typography variant="h6" fontWeight="bold">{systemHealth.aiEngine.predictions_today}</Typography>
            </Box>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="body2">Avg Confidence</Typography>
              <Typography variant="h6" fontWeight="bold">{(systemHealth.aiEngine.avg_confidence * 100).toFixed(1)}%</Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card sx={{ background: 'linear-gradient(135deg, #4caf50 0%, #8bc34a 100%)', color: 'white' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Blockchain Evidence
            </Typography>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h4" fontWeight="bold">
                {systemHealth.blockchain.status.toUpperCase()}
              </Typography>
              <Chip 
                label="IMMUTABLE"
                color="success"
                size="small"
                sx={{ ml: 1 }}
              />
            </Box>
            <Box display="flex" justifyContent="space-between" mb={2}>
              <Typography variant="body2">Total Blocks</Typography>
              <Typography variant="h6" fontWeight="bold">{systemHealth.blockchain.total_blocks}</Typography>
            </Box>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="body2">Integrity Score</Typography>
              <Typography variant="h6" fontWeight="bold">{(blockchainEvidence.integrity_score * 100).toFixed(1)}%</Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card sx={{ background: 'linear-gradient(135deg, #ff9800 0%, #ffb74d 100%)', color: 'white' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Real-Time Monitoring
            </Typography>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h4" fontWeight="bold">
                ACTIVE
              </Typography>
              <Chip 
                label={`${systemHealth.monitoring.active_monitors} MONITORS`}
                color="info"
                size="small"
                sx={{ ml: 1 }}
              />
            </Box>
            <Box display="flex" justifyContent="space-between" mb={2}>
              <Typography variant="body2">Alerts Today</Typography>
              <Typography variant="h6" fontWeight="bold">{systemHealth.monitoring.alerts_today}</Typography>
            </Box>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="body2">WebSocket</Typography>
              <Typography variant="h6" fontWeight="bold">{systemHealth.monitoring.websocket_connections}</Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderPredictions = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              AI Predictions - Risk Analysis
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={predictions.map((p, index) => ({
                name: `Provider ${index + 1}`,
                fraud: p.fraud_probability * 100,
                corruption: p.corruption_probability * 100,
                confidence: p.confidence * 100
              }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="fraud" 
                  stroke="#ff6b6b" 
                  strokeWidth={2}
                />
                <Line 
                  type="monotone" 
                  dataKey="corruption" 
                  stroke="#4caf50" 
                  strokeWidth={2}
                />
                <Line 
                  type="monotone" 
                  dataKey="confidence" 
                  stroke="#2196f3" 
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Fraud Risk Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart data={[
                { name: 'Low Risk', value: 45, fill: '#4caf50' },
                { name: 'Medium Risk', value: 30, fill: '#ff9800' },
                { name: 'High Risk', value: 20, fill: '#ff5722' },
                { name: 'Critical Risk', value: 5, fill: '#f44336' }
              ]}>
                <PieChart />
              <Tooltip />
              <Legend />
            </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" Corruption Risk Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart data={[
                { name: 'Low Risk', value: 60, fill: '#4caf50' },
                { name: 'Medium Risk', value: 25, fill: '#ff9800' },
                { name: 'High Risk', value: 12, fill: '#ff5722' },
                { name: 'Critical Risk', value: 3, fill: '#f44336' }
              ]}>
                <PieChart />
              <Tooltip />
              <Legend />
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderBlockchain = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Blockchain Evidence Integrity
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={[
                { month: 'Jan', integrity: 0.95 },
                { month: 'Feb', integrity: 0.96 },
                { month: 'Mar', integrity: 0.97 },
                { month: 'Apr', integrity: 0.98 }
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis domain={[0.9, 1.0]} />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="integrity" 
                  stroke="#4caf50" 
                  strokeWidth={3}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Evidence Types
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={[
                { type: 'Fraud Analysis', count: 456 },
                { type: 'Political Analysis', count: 234 },
                { type: 'Case Evidence', count: 189 },
                { type: 'Verification', count: 123 },
                { type: 'Audit Trail', count: 89 }
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Verification Status
            </Typography>
            <Box display="flex" flexDirection="column" gap={2}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2">Verified</Typography>
                <Typography variant="h6" fontWeight="bold">{blockchainEvidence.total_entries}</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2">Compromised</Typography>
                <Typography variant="h6" fontWeight="bold">0</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2">Failed</Typography>
                <Typography variant="h6" fontWeight="bold">0</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderMonitoring = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Real-Time Alerts
            </Typography>
            <List>
              {[
                { severity: 'critical', message: 'Unusual political contribution detected during active investigation', provider_name: 'NY Medical Group', timestamp: '2026-02-19T12:15:00Z' },
                { severity: 'high', message: 'Claim frequency spike detected - 150 claims in last hour', provider_name: 'Brooklyn Home Care', timestamp: '2026-02-19T12:10:00Z' },
                { severity: 'medium', message: 'Lobbying activity spike detected', provider_name: 'Queens Pharmacy', timestamp: '2026-02-19T12:05:00Z' },
                { severity: 'low', message: 'Minor billing anomaly detected', provider_name: 'Bronx Medical', timestamp: '2026-02-19T12:00:00Z' }
              ].map((alert, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <IconButton size="small" sx={{ color: getSeverityColor(alert.severity) }}>
                      {getSeverityIcon(alert.severity)}
                    </IconButton>
                  </ListItemIcon>
                  <ListItemText
                    primary={alert.provider_name}
                    secondary={alert.message}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                  <ListItemIcon>
                    <Chip 
                      label={alert.severity.toUpperCase()} 
                      size="small"
                      sx={{ 
                        backgroundColor: getSeverityColor(alert.severity),
                        color: 'white',
                        fontWeight: 'bold',
                        fontSize: '0.7rem'
                      }}
                    />
                  </ListItemIcon>
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" alert_title="Alert Severity Distribution" gutterBottom={2}>
              Alert Severity Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart data={[
                { name: 'Critical', value: 2, fill: '#d32f2f' },
                { name: 'High', value: 8, fill: '#f57c00' },
                { name: 'Medium', value: 15, fill: '#ff9800' },
                { name: 'Low', value: 25, fill: '#4caf50' }
              ]}>
                <PieChart />
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Monitoring Performance
            </Typography>
            <Box display="flex" flexDirection="column" gap={2}>
              <Box>
                <Typography variant="body2" gutterBottom={1}>
                  Active Monitors
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={(systemHealth.monitoring.active_monitors / 20) * 100} 
                  sx={{ backgroundColor: '#e0e0e0' }}
                />
                <Typography variant="caption">{systemHealth.monitoring.active_monitors} / 20}</Typography>
              </Box>
              
              <Box>
                <Typography variant="body2" gutterBottom={1}>
                  Alert Response Time
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={85} 
                  sx={{ backgroundColor: '#4caf50' }}
                />
                <Typography variant="caption">85% under 5 seconds</Typography>
              </Box>
              
              <Box>
                <Typography variant="body2" gutterBottom={1}>
                  WebSocket Connections
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={(systemHealth.monitoring.websocket_connections / 10) * 100} 
                  sx={{ backgroundColor: '#2196f3' }}
                />
                <Typography variant="caption">{systemHealth.monitoring.websocket_connections} / 10}</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderMetrics = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Performance Metrics
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6} md={3}>
                <Box textAlign="center">
                  <Typography variant="h4" color="primary">
                    {systemHealth.aiEngine.predictions_today}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    AI Predictions Today
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} md={3}>
                <Box textAlign="center">
                  <Typography variant="h4" color="success">
                    {(systemHealth.aiEngine.avg_confidence * 100).toFixed(1)}%
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Avg Confidence
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} md={3}>
                <Box textAlign="center">
                  <Typography variant="h4" color="warning">
                    {systemHealth.monitoring.alerts_today}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Alerts Today
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} md={3}>
                <Box textAlign="center">
                  <Typography variant="h4" color="info">
                    {systemHealth.blockchain.total_blocks}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Blockchain Blocks
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              Response Times
            </Typography>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={[
                { time: '00:00', response: 45 },
                { time: '04:00', response: 52 },
                { time: '08:00', response: 38 },
                { time: '12:00', response: 41 },
                { time: '16:00', response: 48 },
                { time: '20:00', response: 35 }
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="response" 
                  stroke="#4caf50" 
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom={2}>
              System Resources
            </Typography>
            <Box display="flex" flexDirection="column" gap={2}>
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2">CPU Usage</Typography>
                <Typography variant="h6" color="warning">67%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={67} sx={{ backgroundColor: '#ff9800' }} />
              
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2">Memory Usage</Typography>
                <Typography variant="h6" color="success">45%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={45} sx={{ backgroundColor: '#4caf50' }} />
              
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2">Database Connections</Typography>
                <Typography variant="h6" color="info">18/20</Typography>
              </Box>
              <LinearProgress variant="determinate" value={90} sx={{ backgroundColor: '#2196f3' }} />
            </Box>
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
        🚀 MediFraudy 2026-2027 Elite Dashboard
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          Real-time monitoring of fraud detection, political corruption analysis, and blockchain evidence integrity.
        </Typography>
      </Alert>
      
      <Box sx={{ mb: 3 }}>
        <Tabs value={selectedTab} onChange={(e, newValue) => setSelectedTab(newValue)}>
          <Tab label="System Health" />
          <Tab label="AI Predictions" />
          <Tab label="Blockchain" />
          <Tab label="Monitoring" />
          <Tab label="Metrics" />
        </Tabs>
      </Box>
      
      {selectedTab === 0 && renderSystemHealth()}
      {selectedTab === 1 && renderPredictions()}
      {selectedTab === 2 && renderBlockchain()}
      {selectedTab === 3 && renderMonitoring()}
      {selectedTab === 4 && renderMetrics()}
    </Box>
  );
};

export default EliteDashboard;
