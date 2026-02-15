import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

interface Alert {
  id: number;
  provider_id: number;
  provider_name: string;
  alert_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  detected_at: string;
  status: 'new' | 'reviewed' | 'dismissed';
}

const severityColors: Record<string, string> = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#64748b',
};

const severityIcons: Record<string, React.ReactNode> = {
  critical: <ErrorIcon sx={{ color: '#ef4444' }} />,
  high: <WarningIcon sx={{ color: '#f59e0b' }} />,
  medium: <InfoIcon sx={{ color: '#3b82f6' }} />,
  low: <InfoIcon sx={{ color: '#64748b' }} />,
};

// Demo alert data for the intelligence platform
const demoAlerts: Alert[] = [
  {
    id: 1, provider_id: 101, provider_name: 'Sunrise Adult Day Care',
    alert_type: 'Capacity Violation', severity: 'critical',
    message: 'Billing 312% above licensed capacity for 14 consecutive days',
    detected_at: '2026-02-14T18:30:00Z', status: 'new',
  },
  {
    id: 2, provider_id: 204, provider_name: 'Brooklyn Home Health Services',
    alert_type: 'Billing Spike', severity: 'high',
    message: 'CPT 97110 volume increased 480% month-over-month',
    detected_at: '2026-02-14T14:15:00Z', status: 'new',
  },
  {
    id: 3, provider_id: 55, provider_name: 'Queens Medical Transport LLC',
    alert_type: 'Impossible Trips', severity: 'high',
    message: '23 trips with physically impossible distances detected',
    detected_at: '2026-02-13T22:00:00Z', status: 'reviewed',
  },
  {
    id: 4, provider_id: 312, provider_name: 'Bronx Elder Care Associates',
    alert_type: 'Network Risk', severity: 'medium',
    message: 'Provider connected to 4 previously sanctioned entities',
    detected_at: '2026-02-13T16:45:00Z', status: 'new',
  },
  {
    id: 5, provider_id: 178, provider_name: 'Manhattan DME Supply Corp',
    alert_type: 'DME Abuse', severity: 'medium',
    message: 'Repeat wheelchair orders: 8.2 per patient average',
    detected_at: '2026-02-13T10:20:00Z', status: 'dismissed',
  },
];

const Alerts: React.FC = () => {
  const navigate = useNavigate();
  const [alerts] = useState<Alert[]>(demoAlerts);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  const filtered = filterSeverity === 'all'
    ? alerts
    : alerts.filter(a => a.severity === filterSeverity);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#f1f5f9', fontWeight: 700 }}>
            ⚡ Fraud Alerts
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748b', mt: 0.5 }}>
            Real-time fraud signal monitoring across all providers
          </Typography>
        </Box>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel sx={{ color: '#94a3b8' }}>Severity</InputLabel>
          <Select
            value={filterSeverity}
            label="Severity"
            onChange={(e) => setFilterSeverity(e.target.value)}
            sx={{ color: '#f1f5f9', '.MuiOutlinedInput-notchedOutline': { borderColor: '#334155' } }}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="critical">Critical</MenuItem>
            <MenuItem value="high">High</MenuItem>
            <MenuItem value="medium">Medium</MenuItem>
            <MenuItem value="low">Low</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Summary Cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2, mb: 3 }}>
        {['critical', 'high', 'medium', 'low'].map((sev) => (
          <Card key={sev} sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b' }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1.5, '&:last-child': { pb: 1.5 } }}>
              {severityIcons[sev]}
              <Box>
                <Typography variant="h5" sx={{ color: severityColors[sev], fontWeight: 700 }}>
                  {alerts.filter(a => a.severity === sev).length}
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748b', textTransform: 'capitalize' }}>
                  {sev}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Alerts Table */}
      <TableContainer component={Paper} sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b' }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Severity</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell>Alert Type</TableCell>
              <TableCell>Details</TableCell>
              <TableCell>Detected</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((alert) => (
              <TableRow
                key={alert.id}
                sx={{
                  '&:hover': { bgcolor: 'rgba(16, 185, 129, 0.03)' },
                  borderLeft: `3px solid ${severityColors[alert.severity]}`,
                }}
              >
                <TableCell>
                  <Chip
                    label={alert.severity.toUpperCase()}
                    size="small"
                    sx={{
                      bgcolor: `${severityColors[alert.severity]}20`,
                      color: severityColors[alert.severity],
                      fontWeight: 700,
                      fontSize: '0.65rem',
                    }}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ color: '#f1f5f9', fontWeight: 600 }}>
                    {alert.provider_name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#64748b' }}>
                    ID: {alert.provider_id}
                  </Typography>
                </TableCell>
                <TableCell sx={{ color: '#94a3b8' }}>{alert.alert_type}</TableCell>
                <TableCell sx={{ color: '#94a3b8', maxWidth: 300 }}>{alert.message}</TableCell>
                <TableCell sx={{ color: '#64748b', fontSize: '0.75rem' }}>
                  {new Date(alert.detected_at).toLocaleString()}
                </TableCell>
                <TableCell>
                  <Chip
                    label={alert.status}
                    size="small"
                    sx={{
                      bgcolor: alert.status === 'new' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(100, 116, 139, 0.1)',
                      color: alert.status === 'new' ? '#10b981' : '#64748b',
                      fontSize: '0.65rem',
                    }}
                  />
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="View Provider">
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/provider/${alert.provider_id}`)}
                      sx={{ color: '#94a3b8', '&:hover': { color: '#10b981' } }}
                    >
                      <ViewIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default Alerts;
