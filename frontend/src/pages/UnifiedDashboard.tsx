import React, { useEffect, useState } from 'react';
import { Download as DownloadIcon, Warning as WarningIcon } from '@mui/icons-material';
import { Typography, Container, Box, CircularProgress, Alert, Button, Card, CardContent, Divider, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip } from '@mui/material';
import axios from 'axios';
import { 
    PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer, Legend 
} from 'recharts';
import { SADCHeatmap } from '../components/dashboard/SADCHeatmap';
import { PharmacyMeter } from '../components/dashboard/PharmacyMeter';
import { RiskScoreCard } from '../components/dashboard/RiskScoreCard';
import { CDPAPNetworkView } from '../components/dashboard/CDPAPNetworkView';
import { NEMTRisks } from '../components/dashboard/NEMTRisks';
import { RecipientRisks } from '../components/dashboard/RecipientRisks';
import { HighRiskFacilities } from '../components/dashboard/HighRiskFacilities';
import { HomeCareView } from '../components/dashboard/HomeCareView';
import { polApi, exportApi, dashboardApi, sadcApi, pharmacyApi, nemtApi, recipientApi, analyticsApi } from '../services/api';

const PIE_COLORS = ['#1976d2', '#d32f2f', '#388e3c', '#f57c00', '#7b1fa2', '#0288d1', '#9c27b0'];

export const UnifiedDashboard: React.FC = () => {
    const [summary, setSummary] = useState<any>(null);
    const [sadcHeatmapData, setSadcHeatmapData] = useState<any>(null);
    const [pharmacyData, setPharmacyData] = useState<any>(null);
    const [nemtGhostRides, setNemtGhostRides] = useState<any[]>([]);
    const [nemtImpossibleTrips, setNemtImpossibleTrips] = useState<any[]>([]);
    const [recipientCardSharers, setRecipientCardSharers] = useState<any[]>([]);
    const [recipientResellers, setRecipientResellers] = useState<any[]>([]);
    const [highRiskFacilities, setHighRiskFacilities] = useState<any[]>([]);
    const [patterns, setPatterns] = useState<any[]>([]);
    const [outliers, setOutliers] = useState<any[]>([]);
    
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                // Fetch all data in parallel with failure handling
                const [
                    summaryRes, 
                    heatmapRes, 
                    pharmacyRes, 
                    ghostRidesRes, 
                    impossibleTripsRes, 
                    cardSharingRes, 
                    resellingRes,
                    sweepRes,
                    outliersRes
                ] = await Promise.allSettled([
                    dashboardApi.getSummary(),
                    sadcApi.getHeatmap(500),
                    pharmacyApi.getLidocaineDumping(1000),
                    nemtApi.getGhostRides(50),
                    nemtApi.getImpossibleTrips(50),
                    recipientApi.getCardSharingSuspects(),
                    recipientApi.getMedicationResellingSuspects(),
                    polApi.getNYCElderlySweep(50),
                    analyticsApi.getOutliers(3, 'NY')
                ]);

                // Helper to extract data or default
                const getData = (res: PromiseSettledResult<any>, defaultVal: any = null) => 
                    res.status === 'fulfilled' ? res.value : defaultVal;
                
                setSummary(getData(summaryRes));
                setSadcHeatmapData(getData(heatmapRes, []));
                setPharmacyData(getData(pharmacyRes, []));
                setNemtGhostRides(getData(ghostRidesRes, []));
                setNemtImpossibleTrips(getData(impossibleTripsRes, []));
                setRecipientCardSharers(getData(cardSharingRes, []));
                setRecipientResellers(getData(resellingRes, []));
                setOutliers(getData(outliersRes, []));
                
                // Handle sweep specifically
                if (sweepRes.status === 'fulfilled') {
                    setHighRiskFacilities(sweepRes.value.results || []);
                } else {
                    console.error("Sweep failed", sweepRes.reason);
                }

                // Log any failures
                if (summaryRes.status === 'rejected') console.error('Summary failed', summaryRes.reason);
                if (heatmapRes.status === 'rejected') console.error('Heatmap failed', heatmapRes.reason);
                if (pharmacyRes.status === 'rejected') console.error('Pharmacy failed', pharmacyRes.reason);

            } catch (err) {
                console.error("Dashboard data load failed (critical)", err);
                setError('Failed to load some dashboard components.');
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, []);

    if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}><CircularProgress /></Box>;
    if (error) return <Alert severity="error">{error}</Alert>;

    // Calculate composite score for the card (average of top 10 risks, or just the max risk found)
    const maxRisk = summary?.top_risks?.[0]?.score || 0;
    const riskBreakdown = {
        sadc: summary?.sadc_count || 0,
        cdpap: summary?.cdpap_count || 0,
        pharmacy: summary?.pharmacy_count || 0,
        recipient: summary?.recipient_count || 0,
        nemt: summary?.nemt_count || 0
    };

    const patternCounts = Array.isArray(patterns) ? patterns.reduce<Record<string, number>>((acc, p) => {
        if (p && p.pattern) {
            acc[p.pattern] = (acc[p.pattern] || 0) + 1;
        }
        return acc;
    }, {}) : {};

    const pieData = Object.entries(patternCounts).map(([name, value]) => ({ 
        name: name.replace(/_/g, ' '), 
        value 
    }));

    const handleDownloadPackage = () => {
        exportApi.downloadDOJPackage();
    };

    return (
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <div>
                    <Typography variant="h4" component="div" sx={{ fontWeight: 'bold', color: '#1a237e' }}>
                        MediFraudy: Unified Dashboard
                    </Typography>
                    <Typography variant="subtitle1" sx={{ color: 'text.secondary' }}>
                        Comprehensive Multi-Vector Surveillance & Forensic Evidence Hub
                    </Typography>
                </div>
                <Button 
                    variant="contained" 
                    color="error" 
                    size="large"
                    startIcon={<DownloadIcon />}
                    onClick={handleDownloadPackage}
                    sx={{ fontWeight: 'bold', boxShadow: 3 }}
                >
                    Download DOJ Referral Package
                </Button>
            </Box>

            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
                {/* TOP ROW: Primary Risks & Pattern Distribution */}
                <Box sx={{ flex: 1 }}>
                    <RiskScoreCard score={maxRisk} breakdown={riskBreakdown} />
                </Box>
                
                <Box sx={{ flex: 1 }}>
                    <Card sx={{ height: '100%' }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>Fraud Pattern Distribution</Typography>
                            <Box sx={{ height: 250 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={pieData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={60}
                                            outerRadius={80}
                                            paddingAngle={5}
                                            dataKey="value"
                                        >
                                            {pieData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <RechartsTooltip />
                                        <Legend />
                                    </PieChart>
                                </ResponsiveContainer>
                            </Box>
                        </CardContent>
                    </Card>
                </Box>

                <Box sx={{ flex: 1 }}>
                    <Card sx={{ height: '100%' }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>Statistical Outliers (z {'>'} 3)</Typography>
                            <TableContainer sx={{ maxHeight: 250 }}>
                                <Table size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Provider</TableCell>
                                            <TableCell align="right">Z-Score</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {outliers.slice(0, 5).map((o: any) => (
                                            <TableRow key={o.provider_id}>
                                                <TableCell>{o.name || `PID: ${o.provider_id}`}</TableCell>
                                                <TableCell align="right">
                                                    <Chip 
                                                        label={o.z_score.toFixed(1)} 
                                                        color="error" 
                                                        size="small" 
                                                        variant="outlined" 
                                                    />
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </CardContent>
                    </Card>
                </Box>

                {/* SECOND ROW: Pharmacy & NYC Sweep */}
                <Box sx={{ flex: 1 }}>
                    <PharmacyMeter data={pharmacyData?.slice(0, 5) || []} />
                </Box>
                <Box sx={{ flex: 1 }}>
                    <HighRiskFacilities facilities={highRiskFacilities} />
                </Box>

                {/* THIRD ROW: NEMT & Recipient Risks */}
                <Box sx={{ flex: 1 }}>
                    <NEMTRisks ghostRides={nemtGhostRides} impossibleTrips={nemtImpossibleTrips} />
                </Box>
                <Box sx={{ flex: 1 }}>
                    <RecipientRisks cardSharers={recipientCardSharers} medResellers={recipientResellers} />
                </Box>

                {/* FOURTH ROW: SADC & Home Care */}
                <Box sx={{ flex: 1 }}>
                    <SADCHeatmap data={sadcHeatmapData || []} />
                </Box>
                <Box sx={{ flex: 1 }}>
                    <HomeCareView />
                </Box>

                {/* BOTTOM ROW: Network Graph */}
                <Box sx={{ width: "100%" }}>
                    <CDPAPNetworkView />
                </Box>
            </Box>
        </Container>
    );
};
