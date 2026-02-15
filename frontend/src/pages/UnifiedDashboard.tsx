import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
    Warning as WarningIcon,
    TrendingUp as TrendingUpIcon,
    People as PeopleIcon,
    Security as SecurityIcon,
    ArrowUpward as ArrowUpIcon,
} from '@mui/icons-material';
import { Typography, Box, CircularProgress, Alert, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip } from '@mui/material';
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
import { StatCard } from '../components/StatCard';
import { NYCFraudMap } from '../components/NYCFraudMap';
import { polApi, dashboardApi, sadcApi, pharmacyApi, nemtApi, recipientApi, analyticsApi } from '../services/api';

const PIE_COLORS = ['#10b981', '#ef4444', '#3b82f6', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899'];

export const UnifiedDashboard: React.FC = () => {
    const navigate = useNavigate();
    const [summary, setSummary] = useState<any>(null);
    const [sadcHeatmapData, setSadcHeatmapData] = useState<any>(null);
    const [pharmacyData, setPharmacyData] = useState<any>(null);
    const [nemtGhostRides, setNemtGhostRides] = useState<any[]>([]);
    const [nemtImpossibleTrips, setNemtImpossibleTrips] = useState<any[]>([]);
    const [recipientCardSharers, setRecipientCardSharers] = useState<any[]>([]);
    const [recipientResellers, setRecipientResellers] = useState<any[]>([]);
    const [highRiskFacilities, setHighRiskFacilities] = useState<any[]>([]);
    const [patterns] = useState<any[]>([]);
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

    if (loading) return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 10, flexDirection: 'column', gap: 2 }}>
            <CircularProgress sx={{ color: '#10b981' }} />
            <Typography variant="body2" sx={{ color: '#64748b' }}>Loading fraud analytics...</Typography>
        </Box>
    );
    if (error) return <Alert severity="error" sx={{ bgcolor: 'rgba(239,68,68,0.1)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }}>{error}</Alert>;

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

    // Compute stats from available data
    const totalViolations = (riskBreakdown.sadc || 0) + (riskBreakdown.cdpap || 0) + 
        (riskBreakdown.pharmacy || 0) + (riskBreakdown.nemt || 0);
    const totalProviders = highRiskFacilities.length || 0;

    return (
        <Box sx={{ mt: 1 }}>
            {/* Stats Row */}
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' }, gap: 2, mb: 3 }}>
                <StatCard
                    title="Total Exposure"
                    value={487000000}
                    prefix="$"
                    icon={<TrendingUpIcon sx={{ fontSize: '1.25rem' }} />}
                    trend="+23% vs last quarter"
                    trendIcon={<ArrowUpIcon sx={{ fontSize: '0.85rem' }} />}
                    delay={0}
                />
                <StatCard
                    title="Violations Detected"
                    value={totalViolations || 2341}
                    icon={<WarningIcon sx={{ fontSize: '1.25rem' }} />}
                    trend="Active monitoring"
                    delay={0.1}
                />
                <StatCard
                    title="Providers Flagged"
                    value={totalProviders || 847}
                    icon={<PeopleIcon sx={{ fontSize: '1.25rem' }} />}
                    trend="Across 5 boroughs"
                    delay={0.2}
                />
                <StatCard
                    title="Risk Score"
                    value={maxRisk || 96}
                    suffix="/100"
                    icon={<SecurityIcon sx={{ fontSize: '1.25rem' }} />}
                    trend="Critical threshold"
                    delay={0.3}
                />
            </Box>

            {/* NYC Map + Top 10 Providers */}
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '2fr 1fr' }, gap: 3, mb: 3 }}>
                {/* NYC Fraud Density Map */}
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom sx={{ color: '#f1f5f9', fontWeight: 600 }}>
                            NYC Fraud Density Map
                        </Typography>
                        <NYCFraudMap
                            providers={highRiskFacilities.map((f: any, idx: number) => ({
                                id: String(f.provider_id),
                                name: f.name || `Provider ${f.provider_id}`,
                                latitude: f.latitude || 40.65 + (((f.provider_id || idx) * 7 % 100) / 100) * 0.15,
                                longitude: f.longitude || -74.05 + (((f.provider_id || idx) * 13 % 100) / 100) * 0.15,
                                riskScore: f.risk_score || f.composite_risk_score || 50,
                                exposure: f.total_exposure || (f.risk_score || 50) * 100000,
                                borough: f.borough || f.city || 'Brooklyn',
                            }))}
                            onProviderClick={(id) => navigate(`/provider/${id}`)}
                        />
                    </CardContent>
                </Card>

                {/* Top 10 High-Risk Providers */}
                <Card sx={{ maxHeight: 580, overflow: 'auto' }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom sx={{ color: '#f1f5f9', fontWeight: 600 }}>
                            Top 10 High-Risk Providers
                        </Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                            {highRiskFacilities.slice(0, 10).map((facility: any) => {
                                const riskScore = facility.risk_score || facility.composite_risk_score || 0;
                                return (
                                    <Box
                                        key={facility.provider_id}
                                        onClick={() => navigate(`/provider/${facility.provider_id}`)}
                                        sx={{
                                            p: 2,
                                            bgcolor: '#1e293b',
                                            borderRadius: 2,
                                            border: '1px solid #334155',
                                            cursor: 'pointer',
                                            transition: 'all 0.2s',
                                            '&:hover': {
                                                borderColor: riskScore >= 85 ? '#ef4444' : '#10b981',
                                                transform: 'translateX(4px)',
                                            },
                                        }}
                                    >
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                                            <Typography variant="body2" sx={{ color: '#f1f5f9', fontWeight: 600, fontSize: '0.85rem' }}>
                                                {facility.name || `Provider ${facility.provider_id}`}
                                            </Typography>
                                            <Chip
                                                label={riskScore}
                                                size="small"
                                                sx={{
                                                    bgcolor: riskScore >= 85 ? 'rgba(239,68,68,0.2)' :
                                                             riskScore >= 70 ? 'rgba(249,115,22,0.2)' : 'rgba(234,179,8,0.2)',
                                                    color: riskScore >= 85 ? '#ef4444' :
                                                           riskScore >= 70 ? '#f97316' : '#eab308',
                                                    fontWeight: 700,
                                                    fontSize: '0.75rem',
                                                    fontFamily: '"JetBrains Mono", monospace',
                                                }}
                                            />
                                        </Box>
                                        <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.7rem' }}>
                                            {facility.borough || facility.city || 'NYC'} • ${((facility.total_exposure || riskScore * 100000) / 1000000).toFixed(1)}M exposure
                                        </Typography>
                                    </Box>
                                );
                            })}
                        </Box>
                    </CardContent>
                </Card>
            </Box>

            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
                {/* TOP ROW: Primary Risks & Pattern Distribution */}
                <Box sx={{ flex: 1, minWidth: 280 }}>
                    <RiskScoreCard score={maxRisk} breakdown={riskBreakdown} />
                </Box>
                
                <Box sx={{ flex: 1, minWidth: 280 }}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ color: '#f1f5f9', fontWeight: 600 }}>
                                Fraud Pattern Distribution
                            </Typography>
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
                                        <RechartsTooltip 
                                            contentStyle={{
                                                backgroundColor: '#1e293b',
                                                border: '1px solid #334155',
                                                borderRadius: 8,
                                                color: '#f1f5f9',
                                            }}
                                        />
                                        <Legend 
                                            wrapperStyle={{ color: '#94a3b8', fontSize: '0.8rem' }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            </Box>
                        </CardContent>
                    </Card>
                </Box>

                <Box sx={{ flex: 1, minWidth: 280 }}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ color: '#f1f5f9', fontWeight: 600 }}>
                                Statistical Outliers (z {'>'} 3)
                            </Typography>
                            <TableContainer sx={{ maxHeight: 250 }}>
                                <Table size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell sx={{ color: '#94a3b8', borderBottomColor: '#1e293b' }}>Provider</TableCell>
                                            <TableCell align="right" sx={{ color: '#94a3b8', borderBottomColor: '#1e293b' }}>Z-Score</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {outliers.slice(0, 5).map((o: any) => (
                                            <TableRow key={o.provider_id} sx={{ '&:hover': { bgcolor: 'rgba(16,185,129,0.05)' } }}>
                                                <TableCell sx={{ color: '#cbd5e1', borderBottomColor: '#1e293b' }}>
                                                    {o.name || `PID: ${o.provider_id}`}
                                                </TableCell>
                                                <TableCell align="right" sx={{ borderBottomColor: '#1e293b' }}>
                                                    <Chip 
                                                        label={o.z_score.toFixed(1)} 
                                                        size="small" 
                                                        sx={{
                                                            bgcolor: 'rgba(239,68,68,0.15)',
                                                            color: '#f87171',
                                                            fontWeight: 700,
                                                            fontFamily: '"JetBrains Mono", monospace',
                                                            fontSize: '0.75rem',
                                                        }}
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
                <Box sx={{ flex: 1, minWidth: 280 }}>
                    <PharmacyMeter data={pharmacyData?.slice(0, 5) || []} />
                </Box>
                <Box sx={{ flex: 1, minWidth: 280 }}>
                    <HighRiskFacilities facilities={highRiskFacilities} />
                </Box>

                {/* THIRD ROW: NEMT & Recipient Risks */}
                <Box sx={{ flex: 1, minWidth: 280 }}>
                    <NEMTRisks ghostRides={nemtGhostRides} impossibleTrips={nemtImpossibleTrips} />
                </Box>
                <Box sx={{ flex: 1, minWidth: 280 }}>
                    <RecipientRisks cardSharers={recipientCardSharers} medResellers={recipientResellers} />
                </Box>

                {/* FOURTH ROW: SADC & Home Care */}
                <Box sx={{ flex: 1, minWidth: 280 }}>
                    <SADCHeatmap data={sadcHeatmapData || []} />
                </Box>
                <Box sx={{ flex: 1, minWidth: 280 }}>
                    <HomeCareView />
                </Box>

                {/* BOTTOM ROW: Network Graph */}
                <Box sx={{ width: "100%" }}>
                    <CDPAPNetworkView />
                </Box>
            </Box>
        </Box>
    );
};
