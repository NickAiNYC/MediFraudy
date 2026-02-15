import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Grid,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Assignment as AssignmentIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { caseApi, InvestigationQueueItem } from '../services/api';

const priorityColors: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  high: 'error',
  medium: 'warning',
  low: 'info',
};

const statusColors: Record<string, 'error' | 'warning' | 'success' | 'info' | 'default'> = {
  new: 'info',
  assigned: 'warning',
  in_progress: 'warning',
  legal_review: 'error',
  closed: 'success',
};

const InvestigationQueue: React.FC = () => {
  const [queue, setQueue] = useState<InvestigationQueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('priority');

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = { sort_by: sortBy };
      if (statusFilter) params.status = statusFilter;
      if (priorityFilter) params.priority = priorityFilter;
      const data = await caseApi.getInvestigationQueue(params);
      setQueue(data.queue || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load investigation queue');
      setQueue([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [statusFilter, priorityFilter, sortBy]);

  const formatCurrency = (amount?: number) => {
    if (!amount) return '—';
    return `$${amount.toLocaleString()}`;
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h5" sx={{ color: '#f1f5f9', fontWeight: 700 }}>
            Investigation Queue
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748b', mt: 0.5 }}>
            {total} active investigations • Ranked by priority and fraud amount
          </Typography>
        </Box>
        <Tooltip title="Refresh Queue">
          <IconButton onClick={fetchQueue} sx={{ color: '#10b981' }}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Summary Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: 'Total Active', value: total, icon: <AssignmentIcon />, color: '#10b981' },
          { label: 'High Priority', value: queue.filter(c => c.priority === 'high').length, icon: <WarningIcon />, color: '#ef4444' },
          { label: 'In Progress', value: queue.filter(c => c.status === 'in_progress').length, icon: <ScheduleIcon />, color: '#f59e0b' },
          { label: 'Closed', value: queue.filter(c => c.status === 'closed').length, icon: <CheckCircleIcon />, color: '#22c55e' },
        ].map((stat) => (
          <Grid item xs={6} md={3} key={stat.label}>
            <Paper sx={{
              p: 2,
              bgcolor: '#0f172a',
              border: '1px solid #1e293b',
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}>
              <Box sx={{ color: stat.color }}>{stat.icon}</Box>
              <Box>
                <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 700 }}>
                  {stat.value}
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748b' }}>
                  {stat.label}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel sx={{ color: '#64748b' }}>Status</InputLabel>
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            label="Status"
            sx={{ color: '#f1f5f9', '.MuiOutlinedInput-notchedOutline': { borderColor: '#334155' } }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="new">New</MenuItem>
            <MenuItem value="assigned">Assigned</MenuItem>
            <MenuItem value="in_progress">In Progress</MenuItem>
            <MenuItem value="legal_review">Legal Review</MenuItem>
            <MenuItem value="closed">Closed</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel sx={{ color: '#64748b' }}>Priority</InputLabel>
          <Select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            label="Priority"
            sx={{ color: '#f1f5f9', '.MuiOutlinedInput-notchedOutline': { borderColor: '#334155' } }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="high">High</MenuItem>
            <MenuItem value="medium">Medium</MenuItem>
            <MenuItem value="low">Low</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel sx={{ color: '#64748b' }}>Sort By</InputLabel>
          <Select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            label="Sort By"
            sx={{ color: '#f1f5f9', '.MuiOutlinedInput-notchedOutline': { borderColor: '#334155' } }}
          >
            <MenuItem value="priority">Priority</MenuItem>
            <MenuItem value="fraud_amount">Fraud Amount</MenuItem>
            <MenuItem value="date">Date</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2, bgcolor: 'rgba(239, 68, 68, 0.1)', color: '#f87171' }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress sx={{ color: '#10b981' }} />
        </Box>
      ) : (
        <TableContainer component={Paper} sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b', borderRadius: 2 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ color: '#94a3b8', fontWeight: 600, borderColor: '#1e293b' }}>Case #</TableCell>
                <TableCell sx={{ color: '#94a3b8', fontWeight: 600, borderColor: '#1e293b' }}>Provider</TableCell>
                <TableCell sx={{ color: '#94a3b8', fontWeight: 600, borderColor: '#1e293b' }}>Priority</TableCell>
                <TableCell sx={{ color: '#94a3b8', fontWeight: 600, borderColor: '#1e293b' }}>Status</TableCell>
                <TableCell sx={{ color: '#94a3b8', fontWeight: 600, borderColor: '#1e293b' }}>Est. Fraud</TableCell>
                <TableCell sx={{ color: '#94a3b8', fontWeight: 600, borderColor: '#1e293b' }}>Assigned To</TableCell>
                <TableCell sx={{ color: '#94a3b8', fontWeight: 600, borderColor: '#1e293b' }}>Source</TableCell>
                <TableCell sx={{ color: '#94a3b8', fontWeight: 600, borderColor: '#1e293b' }}>Opened</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {queue.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} sx={{ color: '#64748b', textAlign: 'center', borderColor: '#1e293b', py: 4 }}>
                    No cases in the investigation queue
                  </TableCell>
                </TableRow>
              ) : (
                queue.map((item) => (
                  <TableRow
                    key={item.id}
                    sx={{
                      '&:hover': { bgcolor: 'rgba(16, 185, 129, 0.05)' },
                      cursor: 'pointer',
                    }}
                  >
                    <TableCell sx={{ color: '#10b981', fontWeight: 600, fontFamily: 'monospace', borderColor: '#1e293b' }}>
                      {item.case_number}
                    </TableCell>
                    <TableCell sx={{ color: '#f1f5f9', borderColor: '#1e293b' }}>
                      Provider #{item.provider_id}
                    </TableCell>
                    <TableCell sx={{ borderColor: '#1e293b' }}>
                      <Chip
                        label={item.priority}
                        size="small"
                        color={priorityColors[item.priority] || 'default'}
                        sx={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.7rem' }}
                      />
                    </TableCell>
                    <TableCell sx={{ borderColor: '#1e293b' }}>
                      <Chip
                        label={item.status?.replace('_', ' ')}
                        size="small"
                        color={statusColors[item.status] || 'default'}
                        variant="outlined"
                        sx={{ fontWeight: 500, fontSize: '0.7rem' }}
                      />
                    </TableCell>
                    <TableCell sx={{ color: '#f59e0b', fontWeight: 600, fontFamily: 'monospace', borderColor: '#1e293b' }}>
                      {formatCurrency(item.estimated_fraud_amount)}
                    </TableCell>
                    <TableCell sx={{ color: '#94a3b8', borderColor: '#1e293b' }}>
                      {item.assigned_to || '—'}
                    </TableCell>
                    <TableCell sx={{ color: '#64748b', borderColor: '#1e293b', fontSize: '0.8rem' }}>
                      {item.detection_source || '—'}
                    </TableCell>
                    <TableCell sx={{ color: '#64748b', borderColor: '#1e293b', fontSize: '0.8rem' }}>
                      {item.opened_at ? new Date(item.opened_at).toLocaleDateString() : '—'}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default InvestigationQueue;
