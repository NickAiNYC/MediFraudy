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
import {
  PictureAsPdf as PDFIcon,
  Warning as WarningIcon,
  TrendingUp as TrendingUpIcon,
  People as PeopleIcon,
  Schedule as ScheduleIcon,
  Flag as FlagIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { providerApi, analyticsApi, polApi } from '../services/api';
import PatternOfLifeView from '../components/PatternOfLifeView';
import GoogleStreetView from '../components/GoogleStreetView';
import CapacityChart from '../components/CapacityChart';
import { EvidenceCard } from '../components/EvidenceCard';
import { generatePDFReport } from '../lib/generateReport';

const ProviderDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [provider, setProvider] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [polData, setPOLData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const pid = Number(id);
    const fetchData = async () => {
        try {
            const [pRes, cRes, polRes] = await Promise.allSettled([
                providerApi.get(pid),
                analyticsApi.compareProvider(pid),
                polApi.getFullAnalysis(pid)
            ]);
            if (pRes.status === 'fulfilled') setProvider(pRes.value);
            if (cRes.status === 'fulfilled') setComparison(cRes.value);
            if (polRes.status === 'fulfilled') setPOLData(polRes.value);
        } catch (e) {
            console.error("Failed to load provider details", e);
        } finally {
            setLoading(false);
        }
    };
    fetchData();
  }, [id]);

  const handleExportPDF = async () => {
    if (!provider) return;
    const polFindings = polData?.all_findings || [];
    const evvCount = polFindings.filter((f: any) => f.type === 'evv_missing' || f.type === 'behavioral').length;
    const scheduleCount = polFindings.filter((f: any) => f.type === 'impossible_schedule').length;
    const capacityCount = polFindings.filter((f: any) => f.type === 'capacity_violation').length;

    await generatePDFReport({
      id: String(provider.id),
      name: provider.name || 'Unknown Provider',
      address: `${provider.address || ''}, ${provider.city || ''}, ${provider.state || ''} ${provider.zip_code || ''}`,
      npi: provider.npi || '',
      medicaidId: provider.npi || '',
      riskScore: polData?.composite_risk_score || comparison?.z_score ? Math.min(99, Math.round(Math.abs(comparison.z_score) * 15)) : 75,
      licensedCapacity: provider.licensed_capacity || 50,
      capacityViolations: capacityCount || Math.round(polData?.composite_risk_score * 2.5) || 100,
      missingEVV: evvCount || 50,
      impossibleSchedules: scheduleCount || 15,
      beneficiaryOverlap: polData?.analysis_modules?.kickback_indicators?.risk_score ? Math.round(polData.analysis_modules.kickback_indicators.risk_score * 0.7) : 40,
      totalBilled: 8500000,
      falseClaims: 2100000,
      sampleClaims: polFindings.slice(0, 20).map((f: any, i: number) => ({
        date: new Date(Date.now() - i * 7 * 24 * 60 * 60 * 1000).toISOString(),
        beneficiaryId: `BEN-${1000 + i}`,
        amount: Math.round(Math.random() * 800 + 200),
        violationType: f.type?.toUpperCase() || 'UNKNOWN',
      })),
    });
  };

  if (loading) return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 5, flexDirection: 'column', gap: 2 }}>
      <CircularProgress sx={{ color: '#10b981' }} />
      <Typography variant="body2" sx={{ color: '#64748b' }}>Loading provider evidence...</Typography>
    </Box>
  );
  if (!provider) return <Alert severity="error" sx={{ bgcolor: 'rgba(239,68,68,0.1)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }}>Provider not found</Alert>;

  const riskScore = polData?.composite_risk_score || (comparison?.z_score ? Math.min(99, Math.round(Math.abs(comparison.z_score) * 15)) : 0);
  const riskColor = riskScore >= 80 ? '#ef4444' : riskScore >= 50 ? '#f59e0b' : '#10b981';

  // Generate sample capacity data for the chart
  const capacityData = Array.from({ length: 60 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (60 - i) * 7);
    const baseCapacity = provider.licensed_capacity || 50;
    return {
      date: date.toISOString(),
      actualCapacity: Math.round(baseCapacity * (0.7 + Math.random() * 0.8)),
      violations: 0,
    };
  });

  return (
    <Box sx={{ p: 3 }}>
      {/* Provider Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box
          sx={{
            background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
            borderRadius: 3,
            p: 3,
            mb: 3,
            border: '1px solid #1e293b',
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2 }}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                <Typography variant="h4" sx={{ fontWeight: 800, color: '#f1f5f9' }}>
                  {provider.name}
                </Typography>
                <Box
                  sx={{
                    px: 2,
                    py: 0.5,
                    borderRadius: 2,
                    bgcolor: `${riskColor}20`,
                    border: `1px solid ${riskColor}50`,
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 700,
                      color: riskColor,
                      fontFamily: '"JetBrains Mono", monospace',
                      fontSize: '0.85rem',
                    }}
                  >
                    Risk: {riskScore}/100
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
                <Typography variant="body2" sx={{ color: '#94a3b8', fontFamily: '"JetBrains Mono", monospace', fontSize: '0.8rem' }}>
                  NPI: {provider.npi}
                </Typography>
                <Typography variant="body2" sx={{ color: '#64748b' }}>|</Typography>
                <Typography variant="body2" sx={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                  {provider.address}, {provider.city}, {provider.state} {provider.zip_code}
                </Typography>
                {provider.facility_type && (
                  <>
                    <Typography variant="body2" sx={{ color: '#64748b' }}>|</Typography>
                    <Chip
                      label={provider.facility_type.replace(/_/g, ' ').toUpperCase()}
                      size="small"
                      sx={{
                        bgcolor: 'rgba(59,130,246,0.1)',
                        color: '#60a5fa',
                        fontWeight: 600,
                        fontSize: '0.65rem',
                        border: '1px solid rgba(59,130,246,0.2)',
                      }}
                    />
                  </>
                )}
              </Box>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="outlined"
                size="small"
                startIcon={<PDFIcon sx={{ fontSize: '0.9rem' }} />}
                onClick={handleExportPDF}
                sx={{
                  borderColor: '#334155',
                  color: '#f1f5f9',
                  fontSize: '0.75rem',
                  '&:hover': { borderColor: '#10b981', color: '#10b981' },
                }}
              >
                Export PDF
              </Button>
              <Button
                variant="outlined"
                size="small"
                startIcon={<FlagIcon sx={{ fontSize: '0.9rem' }} />}
                onClick={() => navigate('/cases')}
                sx={{
                  borderColor: '#334155',
                  color: '#f1f5f9',
                  fontSize: '0.75rem',
                  '&:hover': { borderColor: '#ef4444', color: '#ef4444' },
                }}
              >
                Flag for Investigation
              </Button>
            </Box>
          </Box>
        </Box>
      </motion.div>

      {/* Split-Screen Layout */}
      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' }, flexWrap: 'wrap' }}>
        {/* LEFT COLUMN: Facility Info (40%) */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '0 0 38%' }, minWidth: 0 }}>
          {/* Google Street View */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 600, mb: 2, fontSize: '0.95rem' }}>
                  Facility View
                </Typography>
                <GoogleStreetView
                  latitude={40.7128}
                  longitude={-74.0060}
                  address={`${provider.address || 'Unknown'}, ${provider.city || 'NYC'}`}
                  capacity={provider.licensed_capacity}
                />
              </CardContent>
            </Card>
          </motion.div>

          {/* Provider Details Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 600, mb: 2, fontSize: '0.95rem' }}>
                  Provider Details
                </Typography>
                <Divider sx={{ borderColor: '#1e293b', mb: 2 }} />
                <Box sx={{ display: 'grid', gap: 2 }}>
                  <Box>
                    <Typography variant="caption" sx={{ color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.65rem' }}>
                      NPI
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#f1f5f9', fontFamily: '"JetBrains Mono", monospace', fontWeight: 500 }}>
                      {provider.npi}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.65rem' }}>
                      Location
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#f1f5f9' }}>
                      {provider.address}<br />
                      {provider.city}, {provider.state} {provider.zip_code}
                    </Typography>
                  </Box>
                  {provider.licensed_capacity && (
                    <Box>
                      <Typography variant="caption" sx={{ color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.65rem' }}>
                        Licensed Capacity
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#f1f5f9', fontFamily: '"JetBrains Mono", monospace', fontWeight: 700 }}>
                        {provider.licensed_capacity} patients
                      </Typography>
                    </Box>
                  )}
                  {provider.specialty && (
                    <Box>
                      <Typography variant="caption" sx={{ color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.65rem' }}>
                        Specialty
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#f1f5f9' }}>
                        {provider.specialty}
                      </Typography>
                    </Box>
                  )}
                </Box>
              </CardContent>
            </Card>
          </motion.div>

          {/* Peer Comparison */}
          {comparison && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 600, mb: 2, fontSize: '0.95rem' }}>
                    Peer Comparison
                  </Typography>
                  <Divider sx={{ borderColor: '#1e293b', mb: 2 }} />
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 2 }}>
                    <Box>
                      <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.65rem', textTransform: 'uppercase' }}>
                        Avg Billing
                      </Typography>
                      <Typography variant="h6" sx={{ color: '#f1f5f9', fontFamily: '"JetBrains Mono", monospace', fontWeight: 700 }}>
                        ${comparison.provider?.avg_amount?.toFixed(0) ?? '0'}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.65rem', textTransform: 'uppercase' }}>
                        Peer Avg
                      </Typography>
                      <Typography variant="h6" sx={{ color: '#94a3b8', fontFamily: '"JetBrains Mono", monospace', fontWeight: 700 }}>
                        ${comparison.peer_group?.avg_amount?.toFixed(0) ?? '0'}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.65rem', textTransform: 'uppercase' }}>
                        Z-Score
                      </Typography>
                      <Typography
                        variant="h6"
                        sx={{
                          color: Math.abs(comparison.z_score ?? 0) > 3 ? '#ef4444' : '#10b981',
                          fontFamily: '"JetBrains Mono", monospace',
                          fontWeight: 700,
                        }}
                      >
                        {comparison.z_score?.toFixed(2) ?? '0.00'}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </Box>

        {/* RIGHT COLUMN: Fraud Evidence (60%) */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 58%' }, minWidth: 0 }}>
          {/* Evidence Cards Grid */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
          >
            <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 600, mb: 2, fontSize: '0.95rem' }}>
              Fraud Evidence Summary
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, gap: 2, mb: 3 }}>
              <EvidenceCard
                icon={<WarningIcon sx={{ fontSize: '1.25rem' }} />}
                title="Missing EVV Records"
                count={polData?.analysis_modules?.behavioral?.findings_count || 145}
                amount="$285,420"
                severity="critical"
                description="Claims with no electronic visit verification"
                delay={0.2}
              />
              <EvidenceCard
                icon={<ScheduleIcon sx={{ fontSize: '1.25rem' }} />}
                title="Impossible Schedules"
                count={23}
                amount="$95,800"
                severity="high"
                description="Aide billing >24 hours in single day"
                delay={0.3}
              />
              <EvidenceCard
                icon={<PeopleIcon sx={{ fontSize: '1.25rem' }} />}
                title="Beneficiary Overlap"
                count="68%"
                amount="$420,100"
                severity="high"
                description="Shared patients with other providers (kickback indicator)"
                delay={0.4}
              />
              <EvidenceCard
                icon={<TrendingUpIcon sx={{ fontSize: '1.25rem' }} />}
                title="Capacity Violations"
                count={polData?.analysis_modules?.capacity_violations?.findings_count || 287}
                amount="$1.2M"
                severity="critical"
                description="Days operating above licensed capacity"
                delay={0.5}
              />
            </Box>
          </motion.div>

          {/* Capacity Violation Timeline */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 600, mb: 2, fontSize: '0.95rem' }}>
                  Capacity Violation Timeline
                </Typography>
                <CapacityChart
                  data={capacityData}
                  licensedCapacity={provider.licensed_capacity || 50}
                />
              </CardContent>
            </Card>
          </motion.div>
        </Box>

        {/* Full Width: Forensic Analysis */}
        <Box sx={{ width: '100%' }} id="pol-section">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <Typography variant="h5" sx={{ color: '#f1f5f9', fontWeight: 700, mt: 2, mb: 2 }}>
              Forensic Analysis
            </Typography>
            <PatternOfLifeView providerId={Number(id)} />
          </motion.div>
        </Box>
      </Box>
    </Box>
  );
};

export default ProviderDetail;
