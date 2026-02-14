import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Card, 
  CardContent, 
  Alert,
  CircularProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Stack
} from '@mui/material';
import { Warning, CheckCircle, Error as ErrorIcon } from '@mui/icons-material';
import { apiService } from '../services/api';

interface FacilityResult {
  provider_id: number;
  npi: string;
  name: string;
  city: string;
  facility_type: string;
  risk_score: number;
  severity: string;
  findings_count: number;
}

interface SweepResults {
  analysis_type: string;
  target_facility_types: string[];
  providers_analyzed: number;
  high_risk_facilities: number;
  results: FacilityResult[];
  analysis_timestamp: string;
}

const ElderlyCareDashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [sweepResults, setSweepResults] = useState<SweepResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [minRiskScore, setMinRiskScore] = useState(50);

  const runSweep = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const results = await apiService.getNYCElderlySweep(minRiskScore);
      setSweepResults(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run sweep');
    } finally {
      setLoading(false);
    }
  }, [minRiskScore]);

  useEffect(() => {
    // Auto-run sweep on component mount
    runSweep();
  }, [runSweep]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      default: return 'success';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <ErrorIcon />;
      case 'high': return <Warning />;
      default: return <CheckCircle />;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        NYC Elderly Care Facility Analysis
      </Typography>
      
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Forensic Pattern-of-Life Intelligence for NYC Elderly Care Facilities
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>Recent Prosecutions Context:</strong><br/>
          • Queens $120M case (Feb 9, 2026): Capacity violations, kickbacks, pharmacy fraud<br/>
          • Brooklyn $68M case (Jan 2026): Unprovided services, weekend billing, kickbacks<br/>
          • Albany $1.3M case (Feb 11, 2026): Understaffing, neglect, false claims
        </Typography>
      </Alert>

      <Stack direction="row" spacing={3} sx={{ mb: 3 }}>
        <Box sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Providers Analyzed
              </Typography>
              <Typography variant="h4">
                {sweepResults?.providers_analyzed || 0}
              </Typography>
            </CardContent>
          </Card>
        </Box>
        
        <Box sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                High Risk Facilities
              </Typography>
              <Typography variant="h4" color="error">
                {sweepResults?.high_risk_facilities || 0}
              </Typography>
            </CardContent>
          </Card>
        </Box>
        
        <Box sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Target Facility Types
              </Typography>
              <Typography variant="h4">
                {sweepResults?.target_facility_types.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Box>
        
        <Box sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Results Found
              </Typography>
              <Typography variant="h4">
                {sweepResults?.results.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Box>
      </Stack>

      <Box sx={{ mb: 3 }}>
        <Button 
          variant="contained" 
          onClick={runSweep}
          disabled={loading}
        >
          {loading ? <CircularProgress size={24} /> : 'Run New Sweep'}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading && !sweepResults && (
        <Box display="flex" justifyContent="center" p={5}>
          <CircularProgress />
        </Box>
      )}

      {sweepResults && sweepResults.results.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              High-Risk Facilities
            </Typography>
            
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Severity</TableCell>
                    <TableCell>Facility Name</TableCell>
                    <TableCell>City</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>NPI</TableCell>
                    <TableCell align="right">Risk Score</TableCell>
                    <TableCell align="right">Findings</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sweepResults.results.map((facility) => (
                    <TableRow 
                      key={facility.provider_id}
                      sx={{ 
                        '&:hover': { backgroundColor: 'action.hover' },
                        backgroundColor: facility.severity === 'critical' ? 'rgba(211, 47, 47, 0.05)' : 'inherit'
                      }}
                    >
                      <TableCell>
                        <Chip
                          icon={getSeverityIcon(facility.severity)}
                          label={facility.severity.toUpperCase()}
                          color={getSeverityColor(facility.severity) as any}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {facility.name}
                        </Typography>
                      </TableCell>
                      <TableCell>{facility.city}</TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {facility.facility_type}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" fontFamily="monospace">
                          {facility.npi}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography 
                          variant="body2" 
                          fontWeight="bold"
                          color={facility.risk_score >= 70 ? 'error' : 'inherit'}
                        >
                          {facility.risk_score.toFixed(1)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Chip 
                          label={facility.findings_count} 
                          size="small"
                          color={facility.findings_count > 3 ? 'error' : 'default'}
                        />
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => window.location.href = `/provider/${facility.provider_id}`}
                        >
                          View Details
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {sweepResults && sweepResults.results.length === 0 && (
        <Alert severity="success">
          No high-risk facilities found with current threshold (minimum risk score: {minRiskScore})
        </Alert>
      )}

      {sweepResults && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Analysis completed at: {new Date(sweepResults.analysis_timestamp).toLocaleString()}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default ElderlyCareDashboard;
