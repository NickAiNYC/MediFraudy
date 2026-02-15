import React, { useState, useEffect } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    Button,
    CircularProgress,
    Alert
} from '@mui/material';
import { HomeWork as HomeIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { homecareApi } from '../../services/api';

interface HomeCareAgency {
    provider_id: number;
    name: string;
    npi: string;
    facility_type: string;
    risk_score: number;
    total_billed: number;
    missing_evv_count: number;
    short_visit_count: number;
    claim_count: number;
}

export const HomeCareView: React.FC = () => {
    const navigate = useNavigate();
    const [agencies, setAgencies] = useState<HomeCareAgency[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchAgencies = async () => {
        setLoading(true);
        try {
            const data = await homecareApi.getSweep(40, 50); // Min risk 40, limit 50
            setAgencies(data);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch home care sweep:', err);
            setError('Failed to load home care risk analysis.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAgencies();
    }, []);

    const getRiskColor = (score: number) => {
        if (score >= 70) return 'error';
        if (score >= 40) return 'warning';
        return 'success';
    };

    return (
        <Card sx={{ height: '100%' }}>
            <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <HomeIcon color="primary" sx={{ mr: 1 }} />
                        <Typography variant="h6">Home Care Fraud (EVV & Ghost Visits)</Typography>
                    </Box>
                    <Button 
                        startIcon={<RefreshIcon />} 
                        onClick={fetchAgencies}
                        size="small"
                        disabled={loading}
                    >
                        Refresh
                    </Button>
                </Box>

                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                {loading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                        <CircularProgress />
                    </Box>
                ) : (
                    <TableContainer sx={{ maxHeight: 400 }}>
                        <Table size="small" stickyHeader>
                            <TableHead>
                                <TableRow>
                                    <TableCell>Agency</TableCell>
                                    <TableCell align="right">Risk Score</TableCell>
                                    <TableCell align="right">Missing EVV</TableCell>
                                    <TableCell align="right">Short Visits</TableCell>
                                    <TableCell align="right">Total Billed</TableCell>
                                    <TableCell align="center">Action</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {!Array.isArray(agencies) || agencies.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} align="center">
                                            <Typography variant="body2" sx={{ py: 2 }}>No high-risk agencies found</Typography>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    (Array.isArray(agencies) ? agencies : []).slice(0, 10).map((agency) => (
                                        <TableRow key={agency.provider_id} hover>
                                            <TableCell sx={{ fontWeight: 500 }}>{agency.name}</TableCell>
                                            <TableCell align="right">
                                                <Chip 
                                                    label={agency.risk_score.toFixed(1)} 
                                                    color={getRiskColor(agency.risk_score)}
                                                    size="small"
                                                    variant="outlined"
                                                />
                                            </TableCell>
                                            <TableCell align="right">{agency.missing_evv_count}</TableCell>
                                            <TableCell align="right">{agency.short_visit_count}</TableCell>
                                            <TableCell align="right">
                                                ${(agency.total_billed / 1000).toFixed(1)}k
                                            </TableCell>
                                            <TableCell align="center">
                                                <Button 
                                                    variant="outlined" 
                                                    size="small"
                                                    onClick={() => navigate(`/providers/${agency.provider_id}`)}
                                                >
                                                    Details
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}
            </CardContent>
        </Card>
    );
};
