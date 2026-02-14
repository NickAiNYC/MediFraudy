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
import { listCases, createCase } from '../services/api';

interface Case {
  id: number;
  case_id: string;
  facility_id: number;
  status: string;
  whistleblower_notes: string;
  created_at: string;
}

const CaseManager: React.FC = () => {
  const [cases, setCases] = useState<Case[]>([]);
  const [newCaseId, setNewCaseId] = useState('');
  const [facilityId, setFacilityId] = useState('');
  const [notes, setNotes] = useState('');

  const loadCases = () =>
    listCases().then(({ data }) => setCases(data.cases)).catch(console.error);

  useEffect(() => { loadCases(); }, []);

  const handleCreate = async () => {
    if (!newCaseId || !facilityId) return;
    await createCase(newCaseId, Number(facilityId), notes);
    setNewCaseId('');
    setFacilityId('');
    setNotes('');
    loadCases();
  };

  const statusColor = (s: string) => {
    if (s === 'open') return 'warning';
    if (s === 'closed') return 'success';
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
          <TextField size="small" label="Case ID" value={newCaseId} onChange={(e) => setNewCaseId(e.target.value)} />
          <TextField size="small" label="Facility ID" value={facilityId} onChange={(e) => setFacilityId(e.target.value)} />
          <TextField size="small" label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} multiline />
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
              <TableCell>Facility</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Notes</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {cases.map((c) => (
              <TableRow key={c.id}>
                <TableCell>{c.case_id}</TableCell>
                <TableCell>{c.facility_id}</TableCell>
                <TableCell>
                  <Chip label={c.status} color={statusColor(c.status) as any} size="small" />
                </TableCell>
                <TableCell>{c.whistleblower_notes}</TableCell>
                <TableCell>{c.created_at}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default CaseManager;
