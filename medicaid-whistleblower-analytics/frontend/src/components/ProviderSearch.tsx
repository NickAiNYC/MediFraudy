import React, { useState, useEffect } from 'react';
import {
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Box,
  Typography,
  CircularProgress,
  Chip,
  IconButton,
  Tooltip,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Pagination,
  Alert,
  Snackbar,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import AssessmentIcon from '@mui/icons-material/Assessment';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DownloadIcon from '@mui/icons-material/Download';
import RefreshIcon from '@mui/icons-material/Refresh';
import { 
  searchProviders, 
  getPatternOfLifeSummary, 
  getBatchPatternOfLifeSummaries,
  downloadProviderReport 
} from '../services/api';

interface Provider {
  id: number;
  npi: string;
  name: string;
  city: string;
  state: string;
  facility_type: string;
  licensed_capacity: number | null;
  risk_score?: number;
  risk_level?: 'HIGH' | 'MEDIUM' | 'LOW';
}

interface SearchParams {
  search: string;
  facility_type: string;
  state: string;
  skip: number;
  limit: number;
}

const ProviderSearch: React.FC = () => {
  const navigate = useNavigate();
  
  // Search state
  const [query, setQuery] = useState('');
  const [facilityType, setFacilityType] = useState('');
  const [state, setState] = useState('NY');
  const [results, setResults] = useState<Provider[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [loadingRisk, setLoadingRisk] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Facility type options (from your data)
  const facilityTypes = [
    'adult_day_care',
    'nursing_facility',
    'home_health',
    'rehabilitation',
    'assisted_living',
    'hospital',
    'clinic',
    'pharmacy'
  ];

  const handleSearch = async (pageNum: number = 1) => {
    setLoading(true);
    setError(null);
    
    const params: SearchParams = {
      search: query,
      facility_type: facilityType,
      state: state,
      skip: (pageNum - 1) * limit,
      limit: limit
    };

    try {
      const { data } = await searchProviders(params);
      setResults(data.providers || []);
      setTotalCount(data.total || 0);
      
      // Batch fetch POL summaries if we have providers
      if (data.providers?.length > 0) {
        const providerIds = data.providers.map((p: Provider) => p.id);
        
        try {
          const batchPol = await getBatchPatternOfLifeSummaries(providerIds);
          
          // Merge POL data with providers
          const withRisk = data.providers.map((p: Provider) => ({
            ...p,
            risk_score: batchPol[p.id]?.risk_score,
            risk_level: batchPol[p.id]?.risk_level
          }));
          
          setResults(withRisk);
        } catch (polErr) {
          console.warn('POL summaries not available:', polErr);
          // Continue without POL data
        }
      }
      
      setPage(pageNum);
    } catch (err: any) {
      console.error('Search failed', err);
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  // Handle Enter key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch(1);
    }
  };

  // Handle page change
  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    handleSearch(value);
  };

  // Clear filters
  const handleClearFilters = () => {
    setQuery('');
    setFacilityType('');
    setState('NY');
    handleSearch(1);
  };

  // Refresh POL data for current results
  const handleRefreshRisk = async () => {
    if (results.length === 0) return;
    
    const providerIds = results.map(p => p.id);
    setLoadingRisk(new Set(providerIds));
    
    try {
      const batchPol = await getBatchPatternOfLifeSummaries(providerIds);
      
      const updatedResults = results.map(p => ({
        ...p,
        risk_score: batchPol[p.id]?.risk_score,
        risk_level: batchPol[p.id]?.risk_level
      }));
      
      setResults(updatedResults);
      setSuccessMessage('Risk scores updated');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError('Failed to refresh risk scores');
    } finally {
      setLoadingRisk(new Set());
    }
  };

  // Download report for a provider
  const handleDownloadReport = (providerId: number, providerName: string) => {
    try {
      downloadProviderReport(providerId);
      setSuccessMessage(`Downloading report for ${providerName}`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError('Failed to download report');
    }
  };

  const getRiskColor = (level?: string) => {
    switch(level) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      case 'LOW': return 'success';
      default: return 'default';
    }
  };

  const getRiskIcon = (level?: string) => {
    switch(level) {
      case 'HIGH': return <WarningIcon />;
      case 'MEDIUM': return <ErrorIcon />;
      case 'LOW': return <CheckCircleIcon />;
      default: return null;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Typography variant="h4" gutterBottom>
        Provider Search
        <Chip 
          label="NYC Focus"
          color="primary"
          size="small"
          sx={{ ml: 2 }}
        />
      </Typography>
      
      <Typography variant="body2" color="textSecondary" paragraph>
        Search for providers and view Pattern-of-Life forensic risk scores. 
        High-risk facilities are highlighted in red.
      </Typography>

      {/* Search Controls */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Search by name or NPI"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              size="small"
              placeholder="Enter facility name or NPI..."
            />
          </Grid>
          
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Facility Type</InputLabel>
              <Select
                value={facilityType}
                onChange={(e) => setFacilityType(e.target.value)}
                label="Facility Type"
              >
                <MenuItem value="">All Types</MenuItem>
                {facilityTypes.map(type => (
                  <MenuItem key={type} value={type}>
                    {type.replace(/_/g, ' ').toUpperCase()}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={6} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>State</InputLabel>
              <Select
                value={state}
                onChange={(e) => setState(e.target.value)}
                label="State"
              >
                <MenuItem value="NY">NY</MenuItem>
                <MenuItem value="NJ">NJ</MenuItem>
                <MenuItem value="CT">CT</MenuItem>
                <MenuItem value="">All States</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={6} md={3}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="contained"
                onClick={() => handleSearch(1)}
                disabled={loading}
                fullWidth
              >
                {loading ? <CircularProgress size={24} /> : 'Search'}
              </Button>
              <Tooltip title="Clear filters">
                <Button
                  variant="outlined"
                  onClick={handleClearFilters}
                  disabled={loading}
                >
                  ✕
                </Button>
              </Tooltip>
            </Box>
          </Grid>
        </Grid>

        {/* Results summary */}
        {totalCount > 0 && (
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="body2">
              Found {totalCount} providers
              {results.filter(p => p.risk_level === 'HIGH').length > 0 && (
                <Chip
                  size="small"
                  label={`${results.filter(p => p.risk_level === 'HIGH').length} high risk`}
                  color="error"
                  sx={{ ml: 1 }}
                />
              )}
            </Typography>
            
            <Tooltip title="Refresh risk scores">
              <IconButton size="small" onClick={handleRefreshRisk}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
        )}
      </Paper>

      {/* Error message */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Results table */}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell><strong>NPI</strong></TableCell>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>City</strong></TableCell>
              <TableCell><strong>Type</strong></TableCell>
              <TableCell><strong>Capacity</strong></TableCell>
              <TableCell><strong>Risk Score</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results.map((p) => (
              <TableRow 
                key={p.id}
                sx={{ 
                  backgroundColor: p.risk_level === 'HIGH' 
                    ? 'rgba(211, 47, 47, 0.08)' 
                    : p.risk_level === 'MEDIUM'
                    ? 'rgba(237, 108, 2, 0.04)'
                    : 'inherit',
                  '&:hover': { backgroundColor: '#f5f5f5' },
                  transition: 'background-color 0.2s'
                }}
              >
                <TableCell>{p.npi}</TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {p.name}
                    {p.risk_level && (
                      <Tooltip title={`${p.risk_level} risk facility`}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          {getRiskIcon(p.risk_level)}
                        </Box>
                      </Tooltip>
                    )}
                  </Box>
                </TableCell>
                <TableCell>{p.city}</TableCell>
                <TableCell>
                  <Chip 
                    label={p.facility_type?.replace(/_/g, ' ')}
                    size="small"
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>
                  {p.licensed_capacity ? (
                    <Chip 
                      label={p.licensed_capacity}
                      size="small"
                      color={p.licensed_capacity > 100 ? 'primary' : 'default'}
                    />
                  ) : '—'}
                </TableCell>
                <TableCell>
                  {loadingRisk.has(p.id) ? (
                    <CircularProgress size={20} />
                  ) : p.risk_score ? (
                    <Tooltip title={`${p.risk_level} risk`}>
                      <Chip 
                        label={`${p.risk_score}`}
                        color={getRiskColor(p.risk_level)}
                        size="small"
                        sx={{ fontWeight: 'bold' }}
                      />
                    </Tooltip>
                  ) : (
                    '—'
                  )}
                </TableCell>
                <TableCell align="center">
                  <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
                    <Tooltip title="View Pattern-of-Life Analysis">
                      <IconButton 
                        size="small"
                        onClick={() => navigate(`/providers/${p.id}`)}
                        color="primary"
                      >
                        <AssessmentIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title="Download Report (PDF)">
                      <IconButton 
                        size="small"
                        onClick={() => handleDownloadReport(p.id, p.name)}
                        color="secondary"
                      >
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
            
            {results.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                  <Typography variant="body1" color="textSecondary">
                    No providers found. Try adjusting your search filters.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {totalCount > limit && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Pagination
            count={Math.ceil(totalCount / limit)}
            page={page}
            onChange={handlePageChange}
            color="primary"
            size="large"
            showFirstButton
            showLastButton
          />
        </Box>
      )}

      {/* Success message snackbar */}
      <Snackbar
        open={!!successMessage}
        autoHideDuration={3000}
        onClose={() => setSuccessMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="success" onClose={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      </Snackbar>

      {/* Quick stats footer */}
      {results.length > 0 && (
        <Paper sx={{ mt: 2, p: 2, backgroundColor: '#fafafa' }}>
          <Typography variant="body2" color="textSecondary">
            <strong>Risk Distribution:</strong>{' '}
            {results.filter(p => p.risk_level === 'HIGH').length} High |{' '}
            {results.filter(p => p.risk_level === 'MEDIUM').length} Medium |{' '}
            {results.filter(p => p.risk_level === 'LOW').length} Low
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default ProviderSearch;
