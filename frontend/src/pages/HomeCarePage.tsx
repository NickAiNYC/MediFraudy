import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Paper,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
} from '@mui/material';
import { HomeWork as HomeIcon } from '@mui/icons-material';
import { motion } from 'framer-motion';
import { homecareApi } from '../services/api';

const mono = { fontFamily: '"JetBrains Mono", monospace' };

export const HomeCarePage: React.FC = () => {
  const [sweepData, setSweepData] = useState<any[]>([]);
  const [trendingPatterns, setTrendingPatterns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [_selectedProviderId, setSelectedProviderId] = useState<number | null>(null);
  const [providerDialog, setProviderDialog] = useState(false);
  const [providerIdInput, setProviderIdInput] = useState('');
  const [caseData, setCaseData] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [sweepRes, trendsRes] = await Promise.all([
          homecareApi.getSweep(50, 100).catch(() => []),
          homecareApi.getTrendingPatterns().catch(() => []),
        ]);

        setSweepData(Array.isArray(sweepRes) ? sweepRes : []);
        setTrendingPatterns(Array.isArray(trendsRes) ? trendsRes : []);
        setError('');
      } catch (err: any) {
        console.error('Error fetching home care data:', err);
        setError('Failed to load home care fraud indicators');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleAnalyzeProvider = async () => {
    if (providerIdInput) {
      try {
        const result = await homecareApi.buildFraudCase(parseInt(providerIdInput));
        setCaseData(result);
        setSelectedProviderId(parseInt(providerIdInput));
        setProviderDialog(false);
        setProviderIdInput('');
      } catch (err) {
        setError('Failed to analyze provider');
      }
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 70) return 'error';
    if (score >= 40) return 'warning';
    return 'success';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', flexDirection: 'column', gap: 2, bgcolor: '#020617' }}>
        <CircularProgress sx={{ color: '#10b981' }} />
        <Typography variant="body2" sx={{ color: '#64748b' }}>Loading home care analytics...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ py: 4, px: { xs: 2, md: 4 }, bgcolor: '#020617', minHeight: '100vh' }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Box>
            <Typography
              variant="h4"
              sx={{
                fontWeight: 800,
                background: 'linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                display: 'flex',
                alignItems: 'center',
                letterSpacing: '-0.025em',
              }}
            >
              <HomeIcon sx={{ mr: 2, fontSize: 32, color: '#10b981' }} />
              Home Care Fraud Detection
            </Typography>
            <Typography variant="subtitle1" sx={{ color: '#64748b', mt: 1 }}>
              EVV Violations, Ghost Visits, Kickback Schemes & Homebound Fraud
            </Typography>
          </Box>
          <Button
            variant="contained"
            onClick={() => setProviderDialog(true)}
            sx={{
              height: 'fit-content',
              background: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
              color: '#020617',
              fontWeight: 700,
              px: 3,
              py: 1.5,
              borderRadius: 2,
              boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)',
              '&:hover': {
                background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)',
                boxShadow: '0 6px 20px rgba(16, 185, 129, 0.4)',
              },
            }}
          >
            Analyze Provider
          </Button>
        </Box>
      </motion.div>

      {error && (
        <Alert severity="error" sx={{ mb: 3, bgcolor: 'rgba(239,68,68,0.1)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)', '& .MuiAlert-icon': { color: '#f87171' } }}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 4 }}>
          {[
            { label: 'High-Risk Agencies', value: sweepData.length, gradient: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', accent: '#ef4444' },
            { label: 'Trending Patterns', value: trendingPatterns.length, gradient: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', accent: '#f97316' },
            { label: 'EVV Violations', value: sweepData.filter((d: any) => d.missing_evv_count > 0).length, gradient: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', accent: '#3b82f6' },
            { label: 'Ghost Visits', value: sweepData.filter((d: any) => d.short_visit_count > 0).length, gradient: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', accent: '#10b981' },
          ].map((stat) => (
            <Box
              key={stat.label}
              sx={{
                flex: '1 1 calc(25% - 12px)',
                minWidth: '180px',
                background: stat.gradient,
                borderRadius: 3,
                p: 3,
                border: '1px solid #334155',
                transition: 'all 0.3s ease',
                '&:hover': {
                  borderColor: stat.accent,
                  boxShadow: `0 8px 25px ${stat.accent}22`,
                },
              }}
            >
              <Typography sx={{ color: '#94a3b8', fontSize: '0.85rem', mb: 1 }}>
                {stat.label}
              </Typography>
              <Typography variant="h4" sx={{ color: stat.accent, fontWeight: 800, ...mono }}>
                {stat.value}
              </Typography>
            </Box>
          ))}
        </Box>
      </motion.div>

      {/* High-Risk Agencies Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <Card sx={{ mb: 4, bgcolor: '#0f172a', border: '1px solid #1e293b', borderRadius: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 700, mb: 2 }}>
              High-Risk Home Care Agencies
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ bgcolor: '#0f172a' }}>
                    <TableCell sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Agency Name</TableCell>
                    <TableCell align="right" sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Risk Score</TableCell>
                    <TableCell align="right" sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Missing EVV</TableCell>
                    <TableCell align="right" sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Short Visits</TableCell>
                    <TableCell align="right" sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Total Billed</TableCell>
                    <TableCell align="center" sx={{ color: '#94a3b8', borderBottomColor: '#1e293b', fontWeight: 600 }}>Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sweepData.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 4, borderBottomColor: '#1e293b' }}>
                        <Typography sx={{ color: '#64748b' }}>No high-risk agencies detected</Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    sweepData.slice(0, 15).map((agency: any) => (
                      <TableRow key={agency.provider_id} sx={{ '&:hover': { bgcolor: '#1e293b' } }}>
                        <TableCell sx={{ borderBottomColor: '#1e293b' }}>
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 600, color: '#f1f5f9' }}>
                              {agency.name}
                            </Typography>
                            <Typography variant="caption" sx={{ color: '#64748b', ...mono }}>
                              NPI: {agency.npi}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="right" sx={{ borderBottomColor: '#1e293b' }}>
                          <Chip
                            label={agency.risk_score?.toFixed(1) || 'N/A'}
                            color={getRiskColor(agency.risk_score)}
                            size="small"
                            variant="outlined"
                            sx={{ ...mono, fontWeight: 600 }}
                          />
                        </TableCell>
                        <TableCell align="right" sx={{ borderBottomColor: '#1e293b' }}>
                          <Typography variant="body2" sx={{ color: '#f1f5f9', ...mono }}>{agency.missing_evv_count || 0}</Typography>
                        </TableCell>
                        <TableCell align="right" sx={{ borderBottomColor: '#1e293b' }}>
                          <Typography variant="body2" sx={{ color: '#f1f5f9', ...mono }}>{agency.short_visit_count || 0}</Typography>
                        </TableCell>
                        <TableCell align="right" sx={{ borderBottomColor: '#1e293b' }}>
                          <Typography variant="body2" sx={{ color: '#34d399', fontWeight: 600, ...mono }}>${((agency.total_billed || 0) / 1000).toFixed(1)}k</Typography>
                        </TableCell>
                        <TableCell align="center" sx={{ borderBottomColor: '#1e293b' }}>
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => {
                              setProviderIdInput(agency.provider_id.toString());
                              handleAnalyzeProvider();
                            }}
                            sx={{
                              borderColor: '#334155',
                              color: '#10b981',
                              '&:hover': { borderColor: '#10b981', bgcolor: 'rgba(16,185,129,0.08)' },
                            }}
                          >
                            Analyze
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </motion.div>

      {/* Trending Patterns */}
      {trendingPatterns.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <Card sx={{ mb: 4, bgcolor: '#0f172a', border: '1px solid #1e293b', borderRadius: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 700, mb: 2 }}>
                Trending Fraud Patterns
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                {trendingPatterns.map((pattern: any, idx: number) => (
                  <Paper
                    key={idx}
                    sx={{
                      p: 2,
                      bgcolor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: 2,
                      flex: '1 1 calc(33% - 12px)',
                      minWidth: '200px',
                      transition: 'all 0.3s ease',
                      '&:hover': { borderColor: '#f97316', boxShadow: '0 4px 15px rgba(249,115,22,0.1)' },
                    }}
                  >
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, color: '#f1f5f9' }}>
                      {pattern.pattern_name || pattern.name || `Pattern ${idx + 1}`}
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#94a3b8' }}>
                      {pattern.description || 'Suspicious home care billing pattern detected'}
                    </Typography>
                  </Paper>
                ))}
              </Box>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Detailed Analysis View */}
      {caseData && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <Card sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b', borderRadius: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 700 }}>Fraud Case Analysis</Typography>
                <Button
                  size="small"
                  onClick={() => setCaseData(null)}
                  sx={{ color: '#94a3b8', '&:hover': { color: '#f1f5f9', bgcolor: 'rgba(241,245,249,0.05)' } }}
                >
                  Clear
                </Button>
              </Box>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                <Paper sx={{ p: 2, flex: '1 1 calc(50% - 8px)', minWidth: '200px', bgcolor: '#1e293b', border: '1px solid #334155', borderRadius: 2 }}>
                  <Typography variant="subtitle2" sx={{ color: '#94a3b8', mb: 1 }}>
                    EVV Violations
                  </Typography>
                  <Typography variant="h5" sx={{ color: '#f97316', fontWeight: 800, ...mono }}>{caseData.evv_violations?.count || 0}</Typography>
                  <Typography variant="body2" sx={{ color: '#64748b', ...mono }}>
                    ${((caseData.evv_violations?.amount || 0) / 1000).toFixed(1)}k claimed
                  </Typography>
                </Paper>
                <Paper sx={{ p: 2, flex: '1 1 calc(50% - 8px)', minWidth: '200px', bgcolor: '#1e293b', border: '1px solid #334155', borderRadius: 2 }}>
                  <Typography variant="subtitle2" sx={{ color: '#94a3b8', mb: 1 }}>
                    Ghost Visits Detected
                  </Typography>
                  <Typography variant="h5" sx={{ color: '#3b82f6', fontWeight: 800, ...mono }}>{caseData.ghost_visits?.count || 0}</Typography>
                  <Typography variant="body2" sx={{ color: '#64748b', ...mono }}>
                    ${((caseData.ghost_visits?.amount || 0) / 1000).toFixed(1)}k claimed
                  </Typography>
                </Paper>
                <Paper sx={{ p: 2, flex: '1 1 calc(50% - 8px)', minWidth: '200px', bgcolor: '#1e293b', border: '1px solid #334155', borderRadius: 2 }}>
                  <Typography variant="subtitle2" sx={{ color: '#94a3b8', mb: 1 }}>
                    Homebound Violations
                  </Typography>
                  <Typography variant="h5" sx={{ color: '#f97316', fontWeight: 800, ...mono }}>{caseData.homebound_violations?.count || 0}</Typography>
                  <Typography variant="body2" sx={{ color: '#64748b', ...mono }}>
                    ${((caseData.homebound_violations?.amount || 0) / 1000).toFixed(1)}k claimed
                  </Typography>
                </Paper>
                <Paper sx={{ p: 2, flex: '1 1 calc(50% - 8px)', minWidth: '200px', bgcolor: '#1e293b', border: '1px solid #334155', borderRadius: 2 }}>
                  <Typography variant="subtitle2" sx={{ color: '#94a3b8', mb: 1 }}>
                    Estimated Total Fraud
                  </Typography>
                  <Typography variant="h5" sx={{ color: '#ef4444', fontWeight: 800, ...mono }}>
                    ${((caseData.total_fraud_estimate || 0) / 1000).toFixed(1)}k
                  </Typography>
                </Paper>
              </Box>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Provider Analysis Dialog */}
      <Dialog
        open={providerDialog}
        onClose={() => setProviderDialog(false)}
        PaperProps={{
          sx: {
            bgcolor: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: 3,
            backgroundImage: 'none',
          },
        }}
      >
        <DialogTitle sx={{ color: '#f1f5f9', fontWeight: 700 }}>Analyze Home Care Provider</DialogTitle>
        <DialogContent sx={{ minWidth: 400, pt: 2 }}>
          <TextField
            autoFocus
            fullWidth
            label="Provider ID (NPI)"
            value={providerIdInput}
            onChange={(e) => setProviderIdInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAnalyzeProvider()}
            placeholder="Enter provider NPI..."
            sx={{
              mt: 1,
              '& .MuiOutlinedInput-root': {
                color: '#f1f5f9',
                ...mono,
                '& fieldset': { borderColor: '#334155' },
                '&:hover fieldset': { borderColor: '#10b981' },
                '&.Mui-focused fieldset': { borderColor: '#10b981' },
              },
              '& .MuiInputLabel-root': { color: '#64748b' },
              '& .MuiInputLabel-root.Mui-focused': { color: '#10b981' },
            }}
          />
          <Box sx={{ mt: 3, display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
            <Button
              onClick={() => setProviderDialog(false)}
              sx={{ color: '#94a3b8', '&:hover': { bgcolor: 'rgba(241,245,249,0.05)' } }}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleAnalyzeProvider}
              sx={{
                background: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
                color: '#020617',
                fontWeight: 700,
                '&:hover': { background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)' },
              }}
            >
              Analyze
            </Button>
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default HomeCarePage;
