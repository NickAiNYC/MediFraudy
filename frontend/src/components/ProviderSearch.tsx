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
import DownloadIcon from '@mui/icons-material/Download';
import { motion } from 'framer-motion';
import { providerApi, exportApi, Provider } from '../services/api';

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

const darkSelectMenuProps = {
  PaperProps: {
    sx: {
      bgcolor: '#1e293b',
      border: '1px solid #334155',
      '& .MuiMenuItem-root': {
        color: '#f1f5f9',
        '&:hover': { bgcolor: 'rgba(16,185,129,0.1)' },
        '&.Mui-selected': { bgcolor: 'rgba(16,185,129,0.2)', color: '#10b981' },
        '&.Mui-selected:hover': { bgcolor: 'rgba(16,185,129,0.25)' },
      },
    },
  },
};

const darkInputSx = {
  color: '#f1f5f9',
  bgcolor: '#1e293b',
  borderColor: '#334155',
  '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#10b981' },
  '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#10b981' },
};

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

  const _getRiskColor = (level?: string): 'error' | 'warning' | 'success' | 'default' => {
    switch(level) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      case 'LOW': return 'success';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <Typography variant="h4" gutterBottom sx={{
          fontWeight: 700,
          background: 'linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%)',
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          display: 'inline-flex',
          alignItems: 'center',
        }}>
          Provider Search
        </Typography>
        <Chip
          label="NYC Focus"
          size="small"
          sx={{
            ml: 2,
            bgcolor: 'rgba(16,185,129,0.15)',
            color: '#10b981',
            border: '1px solid rgba(16,185,129,0.3)',
            fontWeight: 600,
          }}
        />
      </motion.div>
      
      <Typography variant="body2" paragraph sx={{ color: '#64748b' }}>
        Search for providers and view Pattern-of-Life forensic risk scores. 
        High-risk facilities are highlighted in red.
      </Typography>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}>
        <Paper sx={{ p: 3, mb: 3, bgcolor: '#0f172a', border: '1px solid #1e293b' }}>
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
                InputProps={{ sx: darkInputSx }}
                InputLabelProps={{ sx: { color: '#64748b' } }}
              />
            </Box>
            
            <Box sx={{ flex: 1, minWidth: '200px' }}>
              <FormControl fullWidth size="small">
                <InputLabel sx={{ color: '#64748b' }}>Facility Type</InputLabel>
                <Select
                  value={facilityType}
                  onChange={(e) => setFacilityType(e.target.value)}
                  label="Facility Type"
                  sx={darkInputSx}
                  MenuProps={darkSelectMenuProps}
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
                <InputLabel sx={{ color: '#64748b' }}>State</InputLabel>
                <Select
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  label="State"
                  sx={darkInputSx}
                  MenuProps={darkSelectMenuProps}
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
                sx={{
                  bgcolor: '#10b981',
                  color: '#fff',
                  '&:hover': { bgcolor: '#059669' },
                  '&.Mui-disabled': { bgcolor: 'rgba(16,185,129,0.3)', color: 'rgba(255,255,255,0.5)' },
                }}
              >
                {loading ? <CircularProgress size={24} sx={{ color: '#fff' }} /> : 'Search'}
              </Button>
              <Tooltip title="Clear filters">
                <Button
                  variant="outlined"
                  onClick={handleClearFilters}
                  disabled={loading}
                  sx={{
                    borderColor: '#334155',
                    color: '#94a3b8',
                    '&:hover': { borderColor: '#10b981', color: '#10b981' },
                  }}
                >
                  Clear
                </Button>
              </Tooltip>
            </Box>
          </Box>

          {totalCount > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" sx={{ color: '#94a3b8' }}>
                Found {totalCount} providers
              </Typography>
            </Box>
          )}
        </Paper>
      </motion.div>

      {error && (
        <Alert
          severity="error"
          sx={{
            mb: 2,
            bgcolor: 'rgba(239,68,68,0.1)',
            color: '#f87171',
            border: '1px solid rgba(239,68,68,0.3)',
            '& .MuiAlert-icon': { color: '#f87171' },
          }}
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.2 }}>
        <TableContainer component={Paper} sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b' }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: '#0f172a' }}>
                <TableCell sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>NPI</TableCell>
                <TableCell sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Name</TableCell>
                <TableCell sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>City</TableCell>
                <TableCell sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Type</TableCell>
                <TableCell sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Capacity</TableCell>
                <TableCell align="center" sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {results.map((p) => (
                <TableRow 
                  key={p.id}
                  sx={{ 
                    '&:hover': { bgcolor: '#1e293b' },
                    transition: 'background-color 0.2s',
                  }}
                >
                  <TableCell sx={{ color: '#94a3b8', fontFamily: '"JetBrains Mono", monospace', borderBottomColor: '#1e293b' }}>{p.npi}</TableCell>
                  <TableCell sx={{ color: '#f1f5f9', borderBottomColor: '#1e293b' }}>{p.name}</TableCell>
                  <TableCell sx={{ color: '#f1f5f9', borderBottomColor: '#1e293b' }}>{p.city}</TableCell>
                  <TableCell sx={{ borderBottomColor: '#1e293b' }}>
                    <Chip 
                      label={p.facility_type?.replace(/_/g, ' ')}
                      size="small"
                      sx={{
                        bgcolor: 'rgba(59,130,246,0.1)',
                        color: '#60a5fa',
                        border: '1px solid rgba(59,130,246,0.2)',
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ borderBottomColor: '#1e293b' }}>
                    {p.licensed_capacity ? (
                      <Chip 
                        label={p.licensed_capacity}
                        size="small"
                        sx={{ bgcolor: '#1e293b', color: '#f1f5f9' }}
                      />
                    ) : '—'}
                  </TableCell>
                  <TableCell align="center" sx={{ borderBottomColor: '#1e293b' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
                      <Tooltip title="View Provider Details">
                        <IconButton 
                          size="small"
                          onClick={() => navigate(`/provider/${p.id}`)}
                          sx={{ color: '#10b981' }}
                        >
                          <AssessmentIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      
                      <Tooltip title="Download Report">
                        <IconButton 
                          size="small"
                          onClick={() => exportApi.downloadProviderReport(p.id)}
                          sx={{ color: '#94a3b8' }}
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
                  <TableCell colSpan={6} align="center" sx={{ py: 4, borderBottomColor: '#1e293b' }}>
                    <Typography variant="body1" sx={{ color: '#64748b' }}>
                      No providers found. Try adjusting your search filters.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </motion.div>

      {totalCount > limit && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Pagination
            count={Math.ceil(totalCount / limit)}
            page={page}
            onChange={handlePageChange}
            sx={{
              '& .MuiPaginationItem-root': { color: '#94a3b8' },
              '& .Mui-selected': { bgcolor: 'rgba(16,185,129,0.2)', color: '#10b981' },
            }}
          />
        </Box>
      )}

      <Snackbar
        open={!!successMessage}
        autoHideDuration={3000}
        onClose={() => setSuccessMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity="success"
          onClose={() => setSuccessMessage(null)}
          sx={{
            bgcolor: 'rgba(16,185,129,0.1)',
            color: '#34d399',
            border: '1px solid rgba(16,185,129,0.3)',
            '& .MuiAlert-icon': { color: '#34d399' },
          }}
        >
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ProviderSearch;
