import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Paper,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
} from '@mui/material';
import { HomeWork as HomeIcon } from '@mui/icons-material';
import { homecareApi } from '../services/api';

export const HomeCarePage: React.FC = () => {
  const [sweepData, setSweepData] = useState<any[]>([]);
  const [trendingPatterns, setTrendingPatterns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [_selectedProviderId, setSelectedProviderId] = useState<number | null>(null);
  const [providerDialog, setProviderDialog] = useState(false);
  const [providerIdInput, setProviderIdInput] = useState('');
  const [caseData, setCaseData] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [sweepRes, trendsRes] = await Promise.all([
          homecareApi.getSweep(50, 100).catch(() => []),
          homecareApi.getTrendingPatterns().catch(() => []),
        ]);

        setSweepData(Array.isArray(sweepRes) ? sweepRes : []);
        setTrendingPatterns(Array.isArray(trendsRes) ? trendsRes : []);
        setError('');
      } catch (err: any) {
        console.error('Error fetching home care data:', err);
        setError('Failed to load home care fraud indicators');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleAnalyzeProvider = async () => {
    if (providerIdInput) {
      try {
        const result = await homecareApi.buildFraudCase(parseInt(providerIdInput));
        setCaseData(result);
        setSelectedProviderId(parseInt(providerIdInput));
        setProviderDialog(false);
        setProviderIdInput('');
      } catch (err) {
        setError('Failed to analyze provider');
      }
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 70) return 'error';
    if (score >= 40) return 'warning';
    return 'success';
  };

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1a237e', display: 'flex', alignItems: 'center' }}>
            <HomeIcon sx={{ mr: 2, fontSize: 32 }} />
            Home Care Fraud Detection
          </Typography>
          <Typography variant="subtitle1" sx={{ color: 'text.secondary', mt: 1 }}>
            EVV Violations, Ghost Visits, Kickback Schemes & Homebound Fraud
          </Typography>
        </Box>
        <Button variant="contained" onClick={() => setProviderDialog(true)} sx={{ height: 'fit-content' }}>
          Analyze Provider
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 4 }}>
        <Card sx={{ flex: '1 1 calc(25% - 8px)', minWidth: '150px' }}>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              High-Risk Agencies
            </Typography>
            <Typography variant="h5">{sweepData.length}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: '1 1 calc(25% - 8px)', minWidth: '150px' }}>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              Trending Patterns
            </Typography>
            <Typography variant="h5">{trendingPatterns.length}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: '1 1 calc(25% - 8px)', minWidth: '150px' }}>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              EVV Violations
            </Typography>
            <Typography variant="h5">{sweepData.filter((d: any) => d.missing_evv_count > 0).length}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: '1 1 calc(25% - 8px)', minWidth: '150px' }}>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              Ghost Visits
            </Typography>
            <Typography variant="h5">{sweepData.filter((d: any) => d.short_visit_count > 0).length}</Typography>
          </CardContent>
        </Card>
      </Box>

      {/* High-Risk Agencies Table */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            High-Risk Home Care Agencies
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                  <TableCell>
                    <strong>Agency Name</strong>
                  </TableCell>
                  <TableCell align="right">
                    <strong>Risk Score</strong>
                  </TableCell>
                  <TableCell align="right">
                    <strong>Missing EVV</strong>
                  </TableCell>
                  <TableCell align="right">
                    <strong>Short Visits</strong>
                  </TableCell>
                  <TableCell align="right">
                    <strong>Total Billed</strong>
                  </TableCell>
                  <TableCell align="center">
                    <strong>Action</strong>
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sweepData.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                      <Typography color="textSecondary">No high-risk agencies detected</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  sweepData.slice(0, 15).map((agency: any) => (
                    <TableRow key={agency.provider_id} hover>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {agency.name}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            NPI: {agency.npi}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <Chip
                          label={agency.risk_score?.toFixed(1) || 'N/A'}
                          color={getRiskColor(agency.risk_score)}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{agency.missing_evv_count || 0}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{agency.short_visit_count || 0}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">${((agency.total_billed || 0) / 1000).toFixed(1)}k</Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => {
                            setProviderIdInput(agency.provider_id.toString());
                            handleAnalyzeProvider();
                          }}
                        >
                          Analyze
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Trending Patterns */}
      {trendingPatterns.length > 0 && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Trending Fraud Patterns
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              {trendingPatterns.map((pattern: any, idx: number) => (
                <Paper key={idx} sx={{ p: 2, backgroundColor: '#f9f9f9', flex: '1 1 calc(33% - 8px)', minWidth: '200px' }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    {pattern.pattern_name || pattern.name || `Pattern ${idx + 1}`}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {pattern.description || 'Suspicious home care billing pattern detected'}
                  </Typography>
                </Paper>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Detailed Analysis View */}
      {caseData && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Fraud Case Analysis</Typography>
              <Button size="small" onClick={() => setCaseData(null)}>
                Clear
              </Button>
            </Box>

            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <Paper sx={{ p: 2, flex: '1 1 calc(50% - 8px)', minWidth: '200px' }}>
                <Typography variant="subtitle2" gutterBottom>
                  EVV Violations
                </Typography>
                <Typography variant="h5">{caseData.evv_violations?.count || 0}</Typography>
                <Typography variant="body2" color="textSecondary">
                  ${((caseData.evv_violations?.amount || 0) / 1000).toFixed(1)}k claimed
                </Typography>
              </Paper>
              <Paper sx={{ p: 2, flex: '1 1 calc(50% - 8px)', minWidth: '200px' }}>
                <Typography variant="subtitle2" gutterBottom>
                  Ghost Visits Detected
                </Typography>
                <Typography variant="h5">{caseData.ghost_visits?.count || 0}</Typography>
                <Typography variant="body2" color="textSecondary">
                  ${((caseData.ghost_visits?.amount || 0) / 1000).toFixed(1)}k claimed
                </Typography>
              </Paper>
              <Paper sx={{ p: 2, flex: '1 1 calc(50% - 8px)', minWidth: '200px' }}>
                <Typography variant="subtitle2" gutterBottom>
                  Homebound Violations
                </Typography>
                <Typography variant="h5">{caseData.homebound_violations?.count || 0}</Typography>
                <Typography variant="body2" color="textSecondary">
                  ${((caseData.homebound_violations?.amount || 0) / 1000).toFixed(1)}k claimed
                </Typography>
              </Paper>
              <Paper sx={{ p: 2, flex: '1 1 calc(50% - 8px)', minWidth: '200px' }}>
                <Typography variant="subtitle2" gutterBottom>
                  Estimated Total Fraud
                </Typography>
                <Typography variant="h5" sx={{ color: 'error.main', fontWeight: 'bold' }}>
                  ${((caseData.total_fraud_estimate || 0) / 1000).toFixed(1)}k
                </Typography>
              </Paper>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Provider Analysis Dialog */}
      <Dialog open={providerDialog} onClose={() => setProviderDialog(false)}>
        <DialogTitle>Analyze Home Care Provider</DialogTitle>
        <DialogContent sx={{ minWidth: 400, pt: 2 }}>
          <TextField
            autoFocus
            fullWidth
            label="Provider ID (NPI)"
            value={providerIdInput}
            onChange={(e) => setProviderIdInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAnalyzeProvider()}
            placeholder="Enter provider NPI..."
          />
          <Box sx={{ mt: 3, display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
            <Button onClick={() => setProviderDialog(false)}>Cancel</Button>
            <Button variant="contained" onClick={handleAnalyzeProvider}>
              Analyze
            </Button>
          </Box>
        </DialogContent>
      </Dialog>
    </Container>
  );
};

export default HomeCarePage;
