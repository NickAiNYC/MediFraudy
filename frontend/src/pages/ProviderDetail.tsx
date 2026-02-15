import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Divider,
  CircularProgress,
  Button,
  Alert
} from '@mui/material';
import { Description as CaseIcon, Assessment as POLIcon } from '@mui/icons-material';
import api from '../services/api';
import PatternOfLifeView from '../components/PatternOfLifeView';

const ProviderDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [provider, setProvider] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const pid = Number(id);
    const fetchData = async () => {
        try {
            const [pRes, cRes] = await Promise.all([
                api.getProvider(pid),
                api.compareProvider(pid)
            ]);
            setProvider(pRes);
            setComparison(cRes);
        } catch (e) {
            console.error("Failed to load provider details", e);
        } finally {
            setLoading(false);
        }
    };
    fetchData();
  }, [id]);

  if (loading) return <Box display="flex" justifyContent="center" p={5}><CircularProgress /></Box>;
  if (!provider) return <Alert severity="error">Provider not found</Alert>;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
            {provider.name}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
            <Button 
                variant="outlined" 
                startIcon={<CaseIcon />}
                onClick={() => navigate('/cases')}
            >
                Manage Case
            </Button>
            <Button 
                variant="contained" 
                color="secondary"
                startIcon={<POLIcon />}
                onClick={() => document.getElementById('pol-section')?.scrollIntoView({ behavior: 'smooth' })}
            >
                View Forensics
            </Button>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' }, flexWrap: 'wrap' }}>
        <Box sx={{ flex: { xs: '100%', md: '30%' }, minWidth: '280px' }}>
            <Card sx={{ height: '100%' }}>
                <CardContent>
                <Typography variant="h6" gutterBottom>Provider Details</Typography>
                <Divider sx={{ mb: 2 }} />
                <Typography variant="subtitle2" color="textSecondary">NPI</Typography>
                <Typography variant="body1" gutterBottom fontFamily="monospace">{provider.npi}</Typography>
                
                <Typography variant="subtitle2" color="textSecondary" sx={{ mt: 2 }}>Location</Typography>
                <Typography variant="body1">
                    {provider.address}<br/>
                    {provider.city}, {provider.state} {provider.zip_code}
                </Typography>

                <Box sx={{ mt: 3 }}>
                    <Chip label={provider.facility_type?.replace(/_/g, ' ').toUpperCase()} color="primary" variant="outlined" sx={{ mr: 1 }} />
                    {provider.licensed_capacity && (
                        <Chip label={`Capacity: ${provider.licensed_capacity}`} color="info" variant="outlined" />
                    )}
                </Box>
                </CardContent>
            </Card>
        </Box>

        <Box sx={{ flex: { xs: '100%', md: '70%' }, minWidth: '280px' }}>
            {comparison && (
                <Card sx={{ height: '100%' }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>Peer Comparison</Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                        <Box sx={{ flex: 1, minWidth: '150px' }}>
                            <Typography variant="subtitle2" color="textSecondary">Average Billing</Typography>
                            <Typography variant="h5">${comparison.provider?.avg_amount?.toFixed(2) ?? '0.00'}</Typography>
                        </Box>
                        <Box sx={{ flex: 1, minWidth: '150px' }}>
                            <Typography variant="subtitle2" color="textSecondary">Peer Average</Typography>
                            <Typography variant="h5">${comparison.peer_group?.avg_amount?.toFixed(2) ?? '0.00'}</Typography>
                        </Box>
                        <Box sx={{ flex: 1, minWidth: '150px' }}>
                            <Typography variant="subtitle2" color="textSecondary">Deviation (Z-Score)</Typography>
                            <Typography 
                                variant="h5" 
                                sx={{ 
                                    color: Math.abs(comparison.z_score ?? 0) > 3 ? 'error.main' : 'success.main',
                                    fontWeight: 'bold'
                                }}
                            >
                                {comparison.z_score?.toFixed(2) ?? '0.00'}
                            </Typography>
                        </Box>
                    </Box>
                    <Alert severity="info" sx={{ mt: 3 }}>
                        Compared against {comparison.peer_group?.count ?? 0} other {provider.facility_type?.replace(/_/g, ' ')} facilities in {provider.state}.
                    </Alert>
                </CardContent>
                </Card>
            )}
        </Box>

        <Box sx={{ width: '100%' }}>
            <Typography variant="h5" gutterBottom sx={{ mt: 4, mb: 2 }}>
                Forensic Analysis
            </Typography>
            <PatternOfLifeView providerId={Number(id)} />
        </Box>
      </Box>
    </Box>
  );
};

export default ProviderDetail;
