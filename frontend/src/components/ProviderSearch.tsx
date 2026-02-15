import React, { useState } from 'react';
import {
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  CircularProgress,
  Chip,
  IconButton,
  Tooltip,
  TextField,
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
import { providerApi, polApi, exportApi, Provider } from '../services/api';

interface ProviderWithRisk extends Provider {
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
  
  const [query, setQuery] = useState('');
  const [facilityType, setFacilityType] = useState('');
  const [state, setState] = useState('NY');
  const [results, setResults] = useState<ProviderWithRisk[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
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
      const response = await providerApi.search(params);
      setResults(response.providers || []);
      setTotalCount(response.count || 0);
      setPage(pageNum);
    } catch (err: any) {
      console.error('Search failed', err);
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch(1);
    }
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    handleSearch(value);
  };

  const handleClearFilters = () => {
    setQuery('');
    setFacilityType('');
    setState('NY');
    handleSearch(1);
  };

  const getRiskColor = (level?: string): 'error' | 'warning' | 'success' | 'default' => {
    switch(level) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      case 'LOW': return 'success';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
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

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <Box sx={{ flex: 1, minWidth: '250px' }}>
            <TextField
              fullWidth
              label="Search by name or NPI"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              size="small"
              placeholder="Enter facility name or NPI..."
            />
          </Box>
          
          <Box sx={{ flex: 1, minWidth: '200px' }}>
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
          </Box>
          
          <Box sx={{ flex: 1, minWidth: '150px' }}>
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
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              onClick={() => handleSearch(1)}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Search'}
            </Button>
            <Tooltip title="Clear filters">
              <Button
                variant="outlined"
                onClick={handleClearFilters}
                disabled={loading}
              >
                Clear
              </Button>
            </Tooltip>
          </Box>
        </Box>

        {totalCount > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2">
              Found {totalCount} providers
            </Typography>
          </Box>
        )}
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell><strong>NPI</strong></TableCell>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>City</strong></TableCell>
              <TableCell><strong>Type</strong></TableCell>
              <TableCell><strong>Capacity</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results.map((p) => (
              <TableRow 
                key={p.id}
                sx={{ 
                  '&:hover': { backgroundColor: '#f5f5f5' },
                  transition: 'background-color 0.2s'
                }}
              >
                <TableCell>{p.npi}</TableCell>
                <TableCell>{p.name}</TableCell>
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
                    />
                  ) : '—'}
                </TableCell>
                <TableCell align="center">
                  <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
                    <Tooltip title="View Provider Details">
                      <IconButton 
                        size="small"
                        onClick={() => navigate(`/providers/${p.id}`)}
                        color="primary"
                      >
                        <AssessmentIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title="Download Report">
                      <IconButton 
                        size="small"
                        onClick={() => exportApi.downloadProviderReport(p.id)}
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
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography variant="body1" color="textSecondary">
                    No providers found. Try adjusting your search filters.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {totalCount > limit && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Pagination
            count={Math.ceil(totalCount / limit)}
            page={page}
            onChange={handlePageChange}
            color="primary"
          />
        </Box>
      )}

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
    </Box>
  );
};

export default ProviderSearch;
