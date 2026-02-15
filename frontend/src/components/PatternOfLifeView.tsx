import React, { useState } from 'react';
import {
  Card, CardContent, Typography, Chip, LinearProgress,
  Button, Alert, Accordion, AccordionSummary, AccordionDetails,
  Box, Paper, Divider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { polApi } from '../services/api';

interface POLAnalysis {
  composite_risk_score: number;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  analysis_modules: {
    behavioral: { risk_score: number; risk_level: string; findings_count: number };
    capacity_violations: { risk_score: number; risk_level: string; findings_count: number };
    kickback_indicators: { risk_score: number; risk_level: string; findings_count: number };
  };
  all_findings: Array<{
    type: string;
    severity: string;
    description: string;
    evidence?: any;
  }>;
  total_findings: number;
  analysis_timestamp: string;
}

export const PatternOfLifeView: React.FC<{ providerId: number }> = ({ providerId }) => {
  const [analysis, setAnalysis] = useState<POLAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await polApi.getFullAnalysis(providerId);
      setAnalysis(response as POLAnalysis); // Type assertion
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to run analysis');
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data from analysis_modules
  const chartData = analysis
    ? [
        { name: 'Behavioral', score: analysis.analysis_modules.behavioral.risk_score, maxScore: 25 },
        { name: 'Capacity', score: analysis.analysis_modules.capacity_violations.risk_score, maxScore: 40 },
        { name: 'Kickback', score: analysis.analysis_modules.kickback_indicators.risk_score, maxScore: 35 },
      ]
    : [];

  const getRiskColor = (severity: string) => {
    switch(severity) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      default: return 'success';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch(severity) {
      case 'HIGH': return <WarningIcon />;
      case 'MEDIUM': return <WarningIcon color="warning" />;
      default: return <CheckCircleIcon color="success" />;
    }
  };

  return (
    <Card elevation={3} sx={{ mt: 3, mb: 3 }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5">
            🔍 Pattern-of-Life Forensic Analysis
          </Typography>
          <Chip
            label="ELITE"
            color="secondary"
            size="small"
            sx={{ fontWeight: 'bold' }}
          />
        </Box>
        
        <Typography variant="body2" color="textSecondary" paragraph>
          Behavioral fingerprint analysis detecting intent signals from recent NY fraud cases.
        </Typography>

        <Button
          variant="contained"
          color="primary"
          onClick={runAnalysis}
          disabled={loading}
          sx={{ mb: 3 }}
        >
          {loading ? <LinearProgress sx={{ width: 100 }} /> : 'Run Elite Analysis'}
        </Button>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {analysis && (
          <>
            <Paper elevation={2} sx={{ p: 3, mb: 3, bgcolor: '#f5f5f5' }}>
              <Box sx={{ display: 'flex', gap: 2, flexDirection: { xs: 'column', md: 'row' }, alignItems: 'center' }}>
                <Box sx={{ flex: { xs: '100%', md: 1 } }}>
                  <Typography variant="h2" color={getRiskColor(analysis.severity)}>
                    {analysis.composite_risk_score}
                  </Typography>
                  <Typography variant="subtitle1">Risk Score (0-100)</Typography>
                </Box>
                <Box sx={{ flex: { xs: '100%', md: 2 } }}>
                  <Alert 
                    severity={getRiskColor(analysis.severity)}
                    icon={getSeverityIcon(analysis.severity)}
                  >
                    <Typography variant="h6">{analysis.severity} RISK</Typography>
                    <Typography>{analysis.total_findings} behavioral indicators detected</Typography>
                  </Alert>
                </Box>
              </Box>
            </Paper>

            <Typography variant="h6" gutterBottom>
              Component Risk Scores
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} layout="vertical">
                <XAxis type="number" domain={[0, 45]} />
                <YAxis type="category" dataKey="name" width={100} />
                <Tooltip />
                <Bar dataKey="score" fill="#1976d2" name="Score" />
              </BarChart>
            </ResponsiveContainer>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h6" gutterBottom>
              Detailed Findings
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {analysis.all_findings.map((finding, index) => (
                <Box key={index} sx={{ width: '100%' }}>
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                        <Chip 
                          size="small"
                          label={finding.type.replace(/_/g, ' ')}
                          variant="outlined"
                        />
                        <Chip 
                          size="small"
                          label={finding.severity}
                          color={finding.severity === 'critical' || finding.severity === 'high' ? 'error' : 'warning'}
                        />
                        <Typography variant="body2" sx={{ flex: 1 }}>
                          {finding.description}
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" color="textSecondary">
                        Evidence: {JSON.stringify(finding.evidence) || 'No additional evidence'}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                </Box>
              ))}
            </Box>

            <Box sx={{ mt: 2, textAlign: 'right' }}>
              <Typography variant="caption" color="textSecondary">
                Analysis generated: {new Date(analysis.analysis_timestamp).toLocaleString()}
              </Typography>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default PatternOfLifeView;
