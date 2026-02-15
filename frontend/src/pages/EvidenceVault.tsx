import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
} from '@mui/material';
import {
  Download as DownloadIcon,
  Description as DocIcon,
  Visibility as ViewIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface EvidenceItem {
  id: number;
  provider_id: number;
  provider_name: string;
  risk_score: number;
  risk_level: string;
  generated_at: string;
  narrative_preview: string;
}

// Demo evidence vault data
const demoEvidence: EvidenceItem[] = [
  {
    id: 1, provider_id: 101, provider_name: 'Sunrise Adult Day Care',
    risk_score: 94, risk_level: 'HIGH', generated_at: '2026-02-14T18:30:00Z',
    narrative_preview: 'Provider Sunrise Adult Day Care has been identified with a composite fraud risk score of 94 out of 100 (HIGH risk). Statistical analysis shows billing at 4.8x the Queens peer average...',
  },
  {
    id: 2, provider_id: 204, provider_name: 'Brooklyn Home Health Services',
    risk_score: 82, risk_level: 'HIGH', generated_at: '2026-02-13T10:00:00Z',
    narrative_preview: 'Provider Brooklyn Home Health Services has been identified with a composite fraud risk score of 82 out of 100 (HIGH risk). Temporal analysis identified 3 billing spikes...',
  },
  {
    id: 3, provider_id: 55, provider_name: 'Queens Medical Transport LLC',
    risk_score: 76, risk_level: 'HIGH', generated_at: '2026-02-12T14:00:00Z',
    narrative_preview: 'Provider Queens Medical Transport LLC has been identified with a composite fraud risk score of 76 out of 100 (HIGH risk). 23 impossible trips detected...',
  },
  {
    id: 4, provider_id: 312, provider_name: 'Bronx Elder Care Associates',
    risk_score: 58, risk_level: 'REVIEW', generated_at: '2026-02-11T09:30:00Z',
    narrative_preview: 'Provider Bronx Elder Care Associates has been identified with a composite fraud risk score of 58 out of 100 (REVIEW risk). Network analysis shows connections to 4 entities...',
  },
];

const riskColors: Record<string, string> = {
  HIGH: '#ef4444',
  REVIEW: '#f59e0b',
  LOW: '#10b981',
};

const EvidenceVault: React.FC = () => {
  const [evidence] = useState<EvidenceItem[]>(demoEvidence);
  const [selectedItem, setSelectedItem] = useState<EvidenceItem | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGeneratePackage = async (providerId: number) => {
    setLoading(true);
    try {
      const response = await axios.get(
        `/api/v1/intelligence/evidence-package/${providerId}`
      );
      // In production, this would trigger a download
      console.log('Evidence package generated:', response.data);
      alert('Evidence package generated successfully. See console for details.');
    } catch (error) {
      console.error('Failed to generate evidence package:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#f1f5f9', fontWeight: 700 }}>
            🗃️ Evidence Vault
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748b', mt: 0.5 }}>
            Litigation-ready evidence packages for qui tam cases
          </Typography>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mb: 3 }}>
        <Card sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b' }}>
          <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Typography variant="caption" sx={{ color: '#64748b' }}>Total Packages</Typography>
            <Typography variant="h4" sx={{ color: '#f1f5f9', fontWeight: 700 }}>{evidence.length}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b' }}>
          <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Typography variant="caption" sx={{ color: '#64748b' }}>High Risk Cases</Typography>
            <Typography variant="h4" sx={{ color: '#ef4444', fontWeight: 700 }}>
              {evidence.filter(e => e.risk_level === 'HIGH').length}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b' }}>
          <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Typography variant="caption" sx={{ color: '#64748b' }}>Under Review</Typography>
            <Typography variant="h4" sx={{ color: '#f59e0b', fontWeight: 700 }}>
              {evidence.filter(e => e.risk_level === 'REVIEW').length}
            </Typography>
          </CardContent>
        </Card>
      </Box>

      {/* Evidence Table */}
      <TableContainer component={Paper} sx={{ bgcolor: '#0f172a', border: '1px solid #1e293b' }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Provider</TableCell>
              <TableCell>Risk Score</TableCell>
              <TableCell>Narrative Preview</TableCell>
              <TableCell>Generated</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {evidence.map((item) => (
              <TableRow key={item.id} sx={{ '&:hover': { bgcolor: 'rgba(16, 185, 129, 0.03)' } }}>
                <TableCell>
                  <Typography variant="body2" sx={{ color: '#f1f5f9', fontWeight: 600 }}>
                    {item.provider_name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#64748b' }}>
                    ID: {item.provider_id}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box
                      sx={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        bgcolor: `${riskColors[item.risk_level]}15`,
                        border: `2px solid ${riskColors[item.risk_level]}`,
                      }}
                    >
                      <Typography variant="body2" sx={{ color: riskColors[item.risk_level], fontWeight: 700 }}>
                        {item.risk_score}
                      </Typography>
                    </Box>
                    <Chip
                      label={item.risk_level}
                      size="small"
                      sx={{
                        bgcolor: `${riskColors[item.risk_level]}20`,
                        color: riskColors[item.risk_level],
                        fontWeight: 700,
                        fontSize: '0.65rem',
                      }}
                    />
                  </Box>
                </TableCell>
                <TableCell sx={{ maxWidth: 350 }}>
                  <Typography variant="body2" sx={{ color: '#94a3b8', fontSize: '0.75rem' }} noWrap>
                    {item.narrative_preview}
                  </Typography>
                </TableCell>
                <TableCell sx={{ color: '#64748b', fontSize: '0.75rem' }}>
                  {new Date(item.generated_at).toLocaleDateString()}
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="View Full Package">
                    <IconButton
                      size="small"
                      onClick={() => setSelectedItem(item)}
                      sx={{ color: '#94a3b8', '&:hover': { color: '#10b981' } }}
                    >
                      <ViewIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Generate Fresh Package">
                    <IconButton
                      size="small"
                      onClick={() => handleGeneratePackage(item.provider_id)}
                      disabled={loading}
                      sx={{ color: '#94a3b8', '&:hover': { color: '#3b82f6' } }}
                    >
                      {loading ? <CircularProgress size={16} /> : <DownloadIcon fontSize="small" />}
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Detail Dialog */}
      <Dialog
        open={!!selectedItem}
        onClose={() => setSelectedItem(null)}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { bgcolor: '#0f172a', border: '1px solid #334155' } }}
      >
        {selectedItem && (
          <>
            <DialogTitle sx={{ color: '#f1f5f9' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <DocIcon sx={{ color: '#10b981' }} />
                Evidence Package — {selectedItem.provider_name}
              </Box>
            </DialogTitle>
            <DialogContent>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ color: '#64748b', mb: 0.5 }}>Risk Assessment</Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={`Score: ${selectedItem.risk_score}`}
                    sx={{ bgcolor: `${riskColors[selectedItem.risk_level]}20`, color: riskColors[selectedItem.risk_level], fontWeight: 700 }}
                  />
                  <Chip
                    label={selectedItem.risk_level}
                    sx={{ bgcolor: `${riskColors[selectedItem.risk_level]}20`, color: riskColors[selectedItem.risk_level], fontWeight: 700 }}
                  />
                </Box>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ color: '#64748b', mb: 0.5 }}>Litigation Narrative</Typography>
                <Typography variant="body2" sx={{ color: '#94a3b8', lineHeight: 1.8 }}>
                  {selectedItem.narrative_preview}
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ color: '#475569' }}>
                This document contains confidential information prepared for potential False Claims Act litigation.
                Protected by attorney-client privilege.
              </Typography>
            </DialogContent>
            <DialogActions sx={{ borderTop: '1px solid #1e293b', px: 3, py: 2 }}>
              <Button
                onClick={() => setSelectedItem(null)}
                sx={{ color: '#94a3b8' }}
              >
                Close
              </Button>
              <Button
                variant="contained"
                onClick={() => handleGeneratePackage(selectedItem.provider_id)}
                disabled={loading}
                sx={{ bgcolor: '#10b981', '&:hover': { bgcolor: '#059669' } }}
              >
                {loading ? <CircularProgress size={16} /> : 'Generate Full Package'}
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default EvidenceVault;
