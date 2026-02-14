import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  Grid,
  Tab,
  Tabs,
  IconButton,
  Tooltip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Assessment as AssessmentIcon,
  Warning as WarningIcon,
  Download as DownloadIcon,
  Add as AddIcon,
  Timeline as TimelineIcon,
  Error as ErrorIcon,
  CheckCircle as CheckCircleIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
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

import {
  getProvider,
  getPatternOfLife,
  getCapacityViolations,
  getKickbackPatterns,
  getBehavioralPatterns,
  downloadProviderReport,
  createCase,
  addTimelineEvent,
} from '../services/api';

interface Provider {
  id: number;
  npi: string;
  name: string;
  address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  facility_type?: string;
  specialty?: string;
  licensed_capacity?: number | null;
}

interface POLAnalysis {
  composite_risk_score: number;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  analysis_modules: {
    behavioral: { risk_score: number; risk_level: string; findings_count: number };
    capacity_violations: { risk_score: number; risk_level: string; findings_count: number };
    kickback_indicators: { risk_score: number; risk_level: string; findings_count: number };
  };
  all_findings: Array<{
    type: string;
    severity: string;
    description: string;
    evidence?: any;
  }>;
  total_findings: number;
  analysis_timestamp: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel = (props: TabPanelProps) => {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`provider-tabpanel-${index}`}
      aria-labelledby={`provider-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

const PIE_COLORS = ['#d32f2f', '#ed6c02', '#2e7d32', '#1976d2', '#9c27b0'];

const ProviderDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const providerId = parseInt(id || '0');

  const [provider, setProvider] = useState<Provider | null>(null);
  const [polAnalysis, setPolAnalysis] = useState<POLAnalysis | null>(null);
  const [capacityData, setCapacityData] = useState<any[]>([]);
  const [kickbackData, setKickbackData] = useState<any>(null);
  const [behavioralData, setBehavioralData] = useState<any>(null);
  
  const [loading, setLoading] = useState({
    provider: false,
    pol: false,
    capacity: false,
    kickback: false,
    behavioral: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  
  // Case management
  const [caseDialogOpen, setCaseDialogOpen] = useState(false);
  const [caseId, setCaseId] = useState('');
  const [caseNotes, setCaseNotes] = useState('');
  const [creatingCase, setCreatingCase] = useState(false);

  const fetchData = async (lookbackDays: number = 365) => {
    if (!providerId) return;

    setError(null);

    // Fetch provider details
    setLoading(prev => ({ ...prev, provider: true }));
    try {
      const { data } = await getProvider(providerId);
      setProvider(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch provider');
    } finally {
      setLoading(prev => ({ ...prev, provider: false }));
    }

    // Fetch POL analysis
    setLoading(prev => ({ ...prev, pol: true }));
    try {
      const data = await getPatternOfLife(providerId, lookbackDays);
      setPolAnalysis(data);
    } catch (err: any) {
      console.error('POL analysis failed:', err);
    } finally {
      setLoading(prev => ({ ...prev, pol: false }));
    }

    // Fetch capacity violations
    setLoading(prev => ({ ...prev, capacity: true }));
    try {
      const data = await getCapacityViolations(providerId, lookbackDays);
      setCapacityData(data.violations || []);
    } catch (err) {
      console.error('Failed to fetch capacity data:', err);
    } finally {
      setLoading(prev => ({ ...prev, capacity: false }));
    }

    // Fetch kickback patterns
    setLoading(prev => ({ ...prev, kickback: true }));
    try {
      const data = await getKickbackPatterns(providerId, lookbackDays);
      setKickbackData(data);
    } catch (err) {
      console.error('Failed to fetch kickback data:', err);
    } finally {
      setLoading(prev => ({ ...prev, kickback: false }));
    }

    // Fetch behavioral patterns
    setLoading(prev => ({ ...prev, behavioral: true }));
    try {
      const data = await getBehavioralPatterns(providerId, lookbackDays);
      setBehavioralData(data);
    } catch (err) {
      console.error('Failed to fetch behavioral data:', err);
    } finally {
      setLoading(prev => ({ ...prev, behavioral: false }));
    }
  };

  useEffect(() => {
    fetchData();
  }, [providerId]);

  const handleRefresh = () => {
    fetchData();
  };

  const handleDownloadReport = () => {
    if (provider) {
      downloadProviderReport(providerId);
    }
  };

  const handleCreateCase = async () => {
    if (!provider || !caseId.trim()) return;

    setCreatingCase(true);
    try {
      await createCase(caseId, providerId, caseNotes);
      setCaseDialogOpen(false);
      setCaseId('');
      setCaseNotes('');
      // Show success message or navigate to cases
      navigate('/cases');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create case');
    } finally {
      setCreatingCase(false);
    }
  };

  const getRiskColor = (severity?: string) => {
    switch(severity) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      case 'LOW': return 'success';
      default: return 'default';
    }
  };

  const getSeverityIcon = (severity?: string) => {
    switch(severity) {
      case 'HIGH': return <WarningIcon color="error" />;
      case 'MEDIUM': return <ErrorIcon color="warning" />;
      case 'LOW': return <CheckCircleIcon color="success" />;
      default: return null;
    }
  };

  const isLoading = Object.values(loading).some(Boolean);

  if (!providerId) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Invalid provider ID</Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton onClick={() => navigate('/providers')}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5">
            {loading.provider ? 'Loading...' : provider?.name}
          </Typography>
          {polAnalysis && (
            <Chip
              icon={getSeverityIcon(polAnalysis.severity)}
              label={`Risk: ${polAnalysis.composite_risk_score} (${polAnalysis.severity})`}
              color={getRiskColor(polAnalysis.severity)}
              sx={{ fontWeight: 'bold' }}
            />
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh Analysis">
            <IconButton onClick={handleRefresh} disabled={isLoading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Download Report">
            <IconButton onClick={handleDownloadReport} disabled={!provider}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCaseDialogOpen(true)}
            disabled={!provider}
          >
            Create Case
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Provider Info Card */}
      {provider && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 3 }}>
                <Typography variant="subtitle2" color="textSecondary">NPI</Typography>
                <Typography>{provider.npi}</Typography>
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <Typography variant="subtitle2" color="textSecondary">Facility Type</Typography>
                <Typography>{provider.facility_type || 'Unknown'}</Typography>
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <Typography variant="subtitle2" color="textSecondary">Location</Typography>
                <Typography>{[provider.city, provider.state].filter(Boolean).join(', ') || 'Unknown'}</Typography>
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <Typography variant="subtitle2" color="textSecondary">Licensed Capacity</Typography>
                <Typography>{provider.licensed_capacity || 'Not specified'}</Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab label="Pattern-of-Life Analysis" />
          <Tab label="Capacity Violations" />
          <Tab label="Kickback Indicators" />
          <Tab label="Behavioral Patterns" />
          <Tab label="Evidence Timeline" />
        </Tabs>

        {/* POL Analysis Tab */}
        <TabPanel value={tabValue} index={0}>
          {loading.pol ? (
            <LinearProgress />
          ) : polAnalysis ? (
            <Box>
              {/* Risk Score Summary */}
              <Paper sx={{ p: 3, mb: 3, bgcolor: '#f5f5f5' }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid size={{ xs: 12, md: 3 }}>
                    <Typography variant="h2" color={getRiskColor(polAnalysis.severity)}>
                      {polAnalysis.composite_risk_score}
                    </Typography>
                    <Typography variant="subtitle1">Risk Score</Typography>
                  </Grid>
                  <Grid size={{ xs: 12, md: 9 }}>
                    <Alert 
                      severity={getRiskColor(polAnalysis.severity)}
                      icon={getSeverityIcon(polAnalysis.severity)}
                    >
                      <Typography variant="h6">{polAnalysis.severity} RISK</Typography>
                      <Typography>
                        {polAnalysis.total_findings} behavioral indicators detected
                      </Typography>
                    </Alert>
                  </Grid>
                </Grid>
              </Paper>

              {/* Module Scores */}
              <Typography variant="h6" gutterBottom>
                Component Risk Scores
              </Typography>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                {Object.entries(polAnalysis.analysis_modules).map(([key, value]) => (
                  <Grid size={{ xs: 12, md: 4 }} key={key}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="textSecondary">
                          {key.replace(/_/g, ' ')}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                          <Typography variant="h4" color={getRiskColor(value.risk_level)}>
                            {value.risk_score}
                          </Typography>
                          <Chip 
                            label={value.risk_level}
                            color={getRiskColor(value.risk_level)}
                            size="small"
                          />
                        </Box>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          {value.findings_count} findings
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>

              {/* Detailed Findings */}
              <Typography variant="h6" gutterBottom>
                Detailed Findings
              </Typography>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Type</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Description</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {polAnalysis.all_findings.map((finding, idx) => (
                      <TableRow key={idx}>
                        <TableCell>
                          <Chip 
                            label={finding.type.replace(/_/g, ' ')}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={finding.severity}
                            color={getRiskColor(finding.severity)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{finding.description}</TableCell>
                      </TableRow>
                    ))}
                    {polAnalysis.all_findings.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={3} align="center">
                          No findings detected
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          ) : (
            <Alert severity="info">No Pattern-of-Life analysis available</Alert>
          )}
        </TabPanel>

        {/* Capacity Violations Tab */}
        <TabPanel value={tabValue} index={1}>
          {loading.capacity ? (
            <LinearProgress />
          ) : capacityData.length > 0 ? (
            <Box>
              <Typography variant="h6" gutterBottom>
                Capacity Violations (Queens $120M Case Pattern)
              </Typography>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Licensed Capacity</TableCell>
                      <TableCell>Billed Patients</TableCell>
                      <TableCell>Excess</TableCell>
                      <TableCell>Excess %</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {capacityData.map((violation, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{violation.date}</TableCell>
                        <TableCell>{violation.licensed_capacity}</TableCell>
                        <TableCell>{violation.billed_patients}</TableCell>
                        <TableCell>{violation.excess}</TableCell>
                        <TableCell>
                          <Chip 
                            label={`${violation.excess_percentage?.toFixed(1)}%`}
                            color={violation.excess_percentage > 50 ? 'error' : 'warning'}
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          ) : (
            <Alert severity="info">No capacity violations detected</Alert>
          )}
        </TabPanel>

        {/* Kickback Indicators Tab */}
        <TabPanel value={tabValue} index={2}>
          {loading.kickback ? (
            <LinearProgress />
          ) : kickbackData ? (
            <Box>
              <Typography variant="h6" gutterBottom>
                Kickback Indicators (Brooklyn $68M Case Pattern)
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Card>
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary">
                        Beneficiary Concentration
                      </Typography>
                      <Typography variant="h4">
                        {(kickbackData.beneficiary_concentration * 100).toFixed(1)}%
                      </Typography>
                      <Typography variant="body2">
                        Top 5% of patients account for this percentage of claims
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Card>
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary">
                        Gini Coefficient
                      </Typography>
                      <Typography variant="h4">
                        {kickbackData.gini_coefficient?.toFixed(3) || 'N/A'}
                      </Typography>
                      <Typography variant="body2">
                        Higher values indicate extreme concentration
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>
          ) : (
            <Alert severity="info">No kickback indicators detected</Alert>
          )}
        </TabPanel>

        {/* Behavioral Patterns Tab */}
        <TabPanel value={tabValue} index={3}>
          {loading.behavioral ? (
            <LinearProgress />
          ) : behavioralData ? (
            <Box>
              <Typography variant="h6" gutterBottom>
                Behavioral Pattern Analysis
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Card>
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary">
                        Weekend Billing
                      </Typography>
                      <Typography variant="h4">
                        {(behavioralData.weekend_ratio * 100).toFixed(1)}%
                      </Typography>
                      <Typography variant="body2">
                        {behavioralData.weekend_ratio > 0.15 ? '⚠️ Above threshold' : 'Normal'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Card>
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary">
                        Batch Submission
                      </Typography>
                      <Typography variant="h4">
                        {(behavioralData.batch_ratio * 100).toFixed(1)}%
                      </Typography>
                      <Typography variant="body2">
                        Claims submitted in peak hour
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Card>
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary">
                        Robotic Pattern
                      </Typography>
                      <Typography variant="h4">
                        {(behavioralData.robotic_ratio * 100).toFixed(1)}%
                      </Typography>
                      <Typography variant="body2">
                        Identical code+amount claims
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>
          ) : (
            <Alert severity="info">No behavioral pattern data available</Alert>
          )}
        </TabPanel>

        {/* Evidence Timeline Tab */}
        <TabPanel value={tabValue} index={4}>
          <Box>
            <Typography variant="h6" gutterBottom>
              Build Evidence Timeline
            </Typography>
            <Alert severity="info">
              Create a case first to add timeline events and build your evidence package for
              False Claims Act disclosure.
            </Alert>
          </Box>
        </TabPanel>
      </Paper>

      {/* Create Case Dialog */}
      <Dialog open={caseDialogOpen} onClose={() => setCaseDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Case</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Case ID"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="e.g., NYC-2026-001"
              fullWidth
              required
            />
            <TextField
              label="Initial Notes"
              value={caseNotes}
              onChange={(e) => setCaseNotes(e.target.value)}
              multiline
              rows={4}
              placeholder="Describe your initial observations..."
              fullWidth
            />
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select value="open" label="Status">
                <MenuItem value="open">Open</MenuItem>
                <MenuItem value="under_seal">Under Seal</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCaseDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleCreateCase} 
            variant="contained"
            disabled={!caseId.trim() || creatingCase}
          >
            {creatingCase ? <CircularProgress size={24} /> : 'Create Case'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Analysis Timestamp */}
      {polAnalysis && (
        <Box sx={{ mt: 2, textAlign: 'right' }}>
          <Typography variant="caption" color="textSecondary">
            Analysis generated: {new Date(polAnalysis.analysis_timestamp).toLocaleString()}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default ProviderDetail;
