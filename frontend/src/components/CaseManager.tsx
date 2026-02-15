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
import { motion } from 'framer-motion';
import { caseApi, Case } from '../services/api';

const statusChipSx: Record<string, object> = {
  open: { bgcolor: 'rgba(249,115,22,0.15)', color: '#fb923c', border: '1px solid rgba(249,115,22,0.3)' },
  closed: { bgcolor: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' },
  under_seal: { bgcolor: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' },
  filed: { bgcolor: 'rgba(59,130,246,0.15)', color: '#60a5fa', border: '1px solid rgba(59,130,246,0.3)' },
  settled: { bgcolor: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' },
};

const darkInputProps = {
  sx: { color: '#f1f5f9', bgcolor: '#1e293b' },
};

const darkLabelProps = {
  sx: { color: '#64748b' },
};

const cellSx = { color: '#f1f5f9', borderColor: '#1e293b' };

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

  return (
    <Box sx={{ bgcolor: '#020617', minHeight: '100vh', p: 3 }}>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <Typography
          variant="h5"
          gutterBottom
          sx={{
            fontWeight: 700,
            background: 'linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Whistleblower Case Manager
        </Typography>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}>
        <Paper sx={{ p: 2, mb: 3, bgcolor: '#0f172a', border: '1px solid #1e293b', borderRadius: 3 }}>
          <Typography variant="subtitle1" gutterBottom sx={{ color: '#f1f5f9' }}>
            New Case
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField
              size="small"
              label="Provider ID"
              value={providerId}
              onChange={(e) => setProviderId(e.target.value)}
              type="number"
              InputProps={darkInputProps}
              InputLabelProps={darkLabelProps}
              sx={{ '& .MuiOutlinedInput-notchedOutline': { borderColor: '#334155' } }}
            />
            <TextField
              size="small"
              label="Notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              multiline
              sx={{ minWidth: 200, '& .MuiOutlinedInput-notchedOutline': { borderColor: '#334155' } }}
              InputProps={darkInputProps}
              InputLabelProps={darkLabelProps}
            />
            <Button
              variant="contained"
              onClick={handleCreate}
              sx={{ bgcolor: '#10b981', '&:hover': { bgcolor: '#059669' }, textTransform: 'none', fontWeight: 600 }}
            >
              Create
            </Button>
          </Box>
        </Paper>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }}>
        <TableContainer component={Paper} sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b', borderRadius: 3 }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: '#0f172a' }}>
                <TableCell sx={{ color: '#94a3b8', borderColor: '#1e293b', fontWeight: 600 }}>Case ID</TableCell>
                <TableCell sx={{ color: '#94a3b8', borderColor: '#1e293b', fontWeight: 600 }}>Provider ID</TableCell>
                <TableCell sx={{ color: '#94a3b8', borderColor: '#1e293b', fontWeight: 600 }}>Status</TableCell>
                <TableCell sx={{ color: '#94a3b8', borderColor: '#1e293b', fontWeight: 600 }}>Notes</TableCell>
                <TableCell sx={{ color: '#94a3b8', borderColor: '#1e293b', fontWeight: 600 }}>Created</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {cases.map((c) => (
                <TableRow key={c.id} sx={{ '&:hover': { bgcolor: '#1e293b' } }}>
                  <TableCell sx={cellSx}>{c.case_number}</TableCell>
                  <TableCell sx={cellSx}>{c.provider_id}</TableCell>
                  <TableCell sx={cellSx}>
                    <Chip
                      label={c.status}
                      size="small"
                      sx={statusChipSx[c.status] || { bgcolor: '#1e293b', color: '#94a3b8' }}
                    />
                  </TableCell>
                  <TableCell sx={cellSx}>{c.description || '—'}</TableCell>
                  <TableCell sx={{ ...cellSx, fontFamily: '"JetBrains Mono", monospace' }}>
                    {new Date(c.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
              {cases.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ color: '#64748b', borderColor: '#1e293b' }}>
                    No cases found. Create your first case above.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </motion.div>
    </Box>
  );
};

export default CaseManager;