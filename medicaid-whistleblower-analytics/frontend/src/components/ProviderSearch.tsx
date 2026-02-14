import React, { useState } from 'react';
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
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import AssessmentIcon from '@mui/icons-material/Assessment';
import WarningIcon from '@mui/icons-material/Warning';
import { searchProviders, getPatternOfLifeSummary } from '../services/api';

interface Provider {
  id: number;
  npi: string;
  name: string;
  city: string;
  state: string;
  facility_type: string;
  licensed_capacity: number | null;
  risk_score?: number;  // Added from POL summary
  risk_level?: 'HIGH' | 'MEDIUM' | 'LOW';  // Added
}

const ProviderSearch: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingRisk, setLoadingRisk] = useState<number | null>(null);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const { data } = await searchProviders({ search: query, state: 'NY' });
      
      // For each provider, fetch POL summary (optional - could be batched)
      const withRisk = await Promise.all(
        data.providers.map(async (p: Provider) => {
          try {
            const pol = await getPatternOfLifeSummary(p.id);
            return { ...p, risk_score: pol.risk_score, risk_level: pol.risk_level };
          } catch {
            return p; // POL not available yet
          }
        })
      );
      
      setResults(withRisk);
    } catch (err) {
      console.error('Search failed', err);
    } finally {
      setLoading(false);
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

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Provider Search
      </Typography>
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          label="Search by name or NPI"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          size="small"
          sx={{ width: 300 }}
        />
        <Button variant="contained" onClick={handleSearch} disabled={loading}>
          {loading ? <CircularProgress size={20} /> : 'Search'}
        </Button>
      </Box>
      
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>NPI</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>City</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Capacity</TableCell>
              <TableCell>Risk Score</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results.map((p) => (
              <TableRow 
                key={p.id}
                sx={{ 
                  backgroundColor: p.risk_level === 'HIGH' ? '#fff2f0' : 'inherit',
                  '&:hover': { backgroundColor: '#f5f5f5' }
                }}
              >
                <TableCell>{p.npi}</TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {p.name}
                    {p.risk_level === 'HIGH' && (
                      <Tooltip title="High risk facility - review immediately">
                        <WarningIcon color="error" fontSize="small" />
                      </Tooltip>
                    )}
                  </Box>
                </TableCell>
                <TableCell>{p.city}</TableCell>
                <TableCell>{p.facility_type}</TableCell>
                <TableCell>{p.licensed_capacity ?? '—'}</TableCell>
                <TableCell>
                  {p.risk_score ? (
                    <Chip 
                      label={`${p.risk_score}`}
                      color={getRiskColor(p.risk_level)}
                      size="small"
                    />
                  ) : (
                    '—'
                  )}
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="View Pattern-of-Life Analysis">
                    <IconButton 
                      size="small"
                      onClick={() => navigate(`/providers/${p.id}`)}
                    >
                      <AssessmentIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {results.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No providers found. Try a different search.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ProviderSearch;
