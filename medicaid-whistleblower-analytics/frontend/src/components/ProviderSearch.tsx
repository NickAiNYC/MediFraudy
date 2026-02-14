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
} from '@mui/material';
import { searchProviders } from '../services/api';

interface Provider {
  id: number;
  npi: string;
  name: string;
  city: string;
  state: string;
  facility_type: string;
  licensed_capacity: number | null;
}

const ProviderSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const { data } = await searchProviders({ search: query, state: 'NY' });
      setResults(data.providers);
    } catch (err) {
      console.error('Search failed', err);
    } finally {
      setLoading(false);
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
              <TableCell>State</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Capacity</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results.map((p) => (
              <TableRow key={p.id}>
                <TableCell>{p.npi}</TableCell>
                <TableCell>{p.name}</TableCell>
                <TableCell>{p.city}</TableCell>
                <TableCell>{p.state}</TableCell>
                <TableCell>{p.facility_type}</TableCell>
                <TableCell>{p.licensed_capacity ?? '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ProviderSearch;
