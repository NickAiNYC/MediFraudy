import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material';
import { caseApi, Case } from '../services/api';

const CaseManager: React.FC = () => {
  const [cases, setCases] = useState<Case[]>([]);
  const [providerId, setProviderId] = useState('');  // Changed from facilityId
  const [notes, setNotes] = useState('');

  const loadCases = () => {
    caseApi.list()
      .then(response => setCases(response.cases || []))
      .catch(console.error);
  };

  useEffect(() => { loadCases(); }, []);

  const handleCreate = async () => {
    if (!providerId) return;
    try {
      await caseApi.create(Number(providerId), notes);
      setProviderId('');
      setNotes('');
      loadCases();
    } catch (error) {
      console.error('Failed to create case:', error);
    }
  };

  const statusColor = (s: string) => {
    if (s === 'open') return 'warning';
    if (s === 'closed') return 'success';
    if (s === 'under_seal') return 'error';
    if (s === 'filed') return 'info';
    if (s === 'settled') return 'success';
    return 'default';
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Whistleblower Case Manager
      </Typography>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          New Case
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <TextField 
            size="small" 
            label="Provider ID" 
            value={providerId} 
            onChange={(e) => setProviderId(e.target.value)} 
            type="number"
          />
          <TextField 
            size="small" 
            label="Notes" 
            value={notes} 
            onChange={(e) => setNotes(e.target.value)} 
            multiline 
            sx={{ minWidth: 200 }}
          />
          <Button variant="contained" onClick={handleCreate}>
            Create
          </Button>
        </Box>
      </Paper>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Case ID</TableCell>
              <TableCell>Provider ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Notes</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {cases.map((c) => (
              <TableRow key={c.id}>
                <TableCell>{c.case_number}</TableCell>
                <TableCell>{c.provider_id}</TableCell>
                <TableCell>
                  <Chip label={c.status} color={statusColor(c.status) as any} size="small" />
                </TableCell>
                <TableCell>{c.description || '—'}</TableCell>
                <TableCell>{new Date(c.created_at).toLocaleDateString()}</TableCell>
              </TableRow>
            ))}
            {cases.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No cases found. Create your first case above.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default CaseManager;