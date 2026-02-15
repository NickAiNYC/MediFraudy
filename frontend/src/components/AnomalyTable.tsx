import React, { useEffect, useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  Slider,
} from '@mui/material';
import { anomalyApi } from '../services/api';

interface Anomaly {
  id: number;
  provider_id: number;
  billing_code: string;
  z_score: number;
  anomaly_type?: string;  // Made optional with ?
  notes?: string;          // Made optional with ?
  detected_at: string;     // Add this if API returns it
}

const AnomalyTable: React.FC = () => {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [zThreshold, setZThreshold] = useState(3);

  useEffect(() => {
    anomalyApi.list({ min_z_score: zThreshold })
      .then(response => setAnomalies(response.anomalies || []))
      .catch(console.error);
  }, [zThreshold]);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Billing Anomalies
      </Typography>
      <Box sx={{ width: 300, mb: 2 }}>
        <Typography gutterBottom>Z-Score Threshold: {zThreshold}</Typography>
        <Slider
          value={zThreshold}
          onChange={(_, v) => setZThreshold(v as number)}
          min={2}
          max={6}
          step={0.5}
          marks
          valueLabelDisplay="auto"
        />
      </Box>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Provider ID</TableCell>
              <TableCell>Billing Code</TableCell>
              <TableCell>Z-Score</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Notes</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {anomalies.map((a) => (
              <TableRow key={a.id} sx={{ bgcolor: a.z_score > 5 ? '#ffebee' : undefined }}>
                <TableCell>{a.provider_id}</TableCell>
                <TableCell>{a.billing_code}</TableCell>
                <TableCell>{a.z_score.toFixed(2)}</TableCell>
                <TableCell>{a.anomaly_type || '—'}</TableCell>
                <TableCell>{a.notes || '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default AnomalyTable;