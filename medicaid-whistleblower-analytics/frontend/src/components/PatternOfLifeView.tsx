import React, { useState, useEffect } from 'react';
import {
  Card, CardContent, Typography, Grid, Chip, LinearProgress,
  Button, Alert, Accordion, AccordionSummary, AccordionDetails,
  Box, Paper, Divider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../services/api';

interface IndicatorDetail {
  score: number;
  details: string;
  [key: string]: any;
}

interface POLAnalysis {
  provider_id: number;
  provider_name: string;
  risk_score: number;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
  recommendation: string;
  indicators: Record<string, IndicatorDetail>;
  analysis_date: string;
}

export const PatternOfLifeView: React.FC<{ providerId: number }> = ({ providerId }) => {
  const [analysis, setAnalysis] = useState<POLAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/analytics/pol/${providerId}`);
      setAnalysis(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to run analysis');
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data
  const chartData = analysis
    ? Object.entries(analysis.indicators).map(([key, value]) => ({
        name: key.replace(/_/g, ' '),
        score: value.score || 0,
        maxScore: (() => {
          switch(key) {
            case 'sudden_spike': return 20;
            case 'max_code_abuse': return 15;
            case 'timing_anomaly': return 15;
            case 'capacity_exceed': return 25;
            case 'referral_concentration': return 15;
            case 'sustained_no_growth': return 10;
            default: return 15;
          }
        })()
      }))
    : [];

  const getRiskColor = (level: string) => {
    switch(level) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      default: return 'success';
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
          Behavioral fingerprint analysis (matches NSA/CIA methodology) detecting intent signals from recent NY fraud cases.
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
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} md={4}>
                  <Typography variant="h2" color={getRiskColor(analysis.risk_level)}>
                    {analysis.risk_score}
                  </Typography>
                  <Typography variant="subtitle1">Risk Score (0-100)</Typography>
                </Grid>
                <Grid item xs={12} md={8}>
                  <Alert 
                    severity={getRiskColor(analysis.risk_level)}
                    icon={analysis.risk_level === 'HIGH' ? <WarningIcon /> : <CheckCircleIcon />}
                  >
                    <Typography variant="h6">{analysis.risk_level} RISK</Typography>
                    <Typography>{analysis.recommendation}</Typography>
                  </Alert>
                </Grid>
              </Grid>
            </Paper>

            <Typography variant="h6" gutterBottom>
              Indicator Breakdown
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} layout="vertical">
                <XAxis type="number" domain={[0, 25]} />
                <YAxis type="category" dataKey="name" width={150} />
                <Tooltip />
                <Bar dataKey="score" fill="#8884d8" name="Score" />
                <Bar dataKey="maxScore" fill="#ffc658" name="Max" />
              </BarChart>
            </ResponsiveContainer>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h6" gutterBottom>
              Detailed Findings
            </Typography>
            <Grid container spacing={2}>
              {Object.entries(analysis.indicators).map(([key, value]) => (
                <Grid item xs={12} md={6} key={key}>
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography sx={{ fontWeight: 'bold', textTransform: 'capitalize' }}>
                        {key.replace(/_/g, ' ')}
                      </Typography>
                      <Chip 
                        size="small" 
                        label={`Score: ${value.score}`}
                        color={value.score > 10 ? 'error' : value.score > 5 ? 'warning' : 'success'}
                        sx={{ ml: 2 }}
                      />
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2">{value.details}</Typography>
                      {Object.entries(value).map(([k, v]) => {
                        if (k !== 'score' && k !== 'details' && typeof v !== 'object') {
                         
