import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Stack,
} from '@mui/material';
import {
  ExpandMore,
  Warning,
  CheckCircle,
  Error as ErrorIcon,
  Info,
} from '@mui/icons-material';
import { apiService } from '../services/api';

interface Finding {
  type: string;
  severity: string;
  description: string;
  evidence: any;
}

interface ModuleAnalysis {
  provider_id: number;
  provider_name: string;
  pattern_type: string;
  risk_score: number;
  findings: Finding[];
  [key: string]: any;
}

interface PatternOfLifeAnalysis {
  provider_id: number;
  provider_name: string;
  provider_type: string;
  analysis_type: string;
  composite_risk_score: number;
  severity: string;
  analysis_modules: {
    behavioral: ModuleAnalysis;
    capacity_violations: ModuleAnalysis;
    kickback_indicators: ModuleAnalysis;
  };
  all_findings: Finding[];
  total_findings: number;
  analysis_period_days: number;
  analysis_timestamp: string;
}

interface PatternOfLifeViewProps {
  providerId: number;
}

const PatternOfLifeView: React.FC<PatternOfLifeViewProps> = ({ providerId }) => {
  const [analysis, setAnalysis] = useState<PatternOfLifeAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAnalysis();
  }, [providerId]);

  const loadAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getPatternOfLife(providerId);
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analysis');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return <ErrorIcon color="error" />;
      case 'high': return <Warning color="warning" />;
      case 'medium': return <Info color="info" />;
      default: return <CheckCircle color="success" />;
    }
  };

  const getRiskScoreColor = (score: number) => {
    if (score >= 70) return 'error';
    if (score >= 50) return 'warning';
    if (score >= 30) return 'info';
    return 'success';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 3 }}>
        {error}
      </Alert>
    );
  }

  if (!analysis) {
    return (
      <Alert severity="info" sx={{ m: 3 }}>
        No pattern-of-life analysis available for this provider.
      </Alert>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Pattern-of-Life Analysis
      </Typography>
      
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        {analysis.provider_name} ({analysis.provider_type})
      </Typography>

      {/* Summary Cards */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <Box sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>
                Composite Risk Score
              </Typography>
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="h4" color={getRiskScoreColor(analysis.composite_risk_score)}>
                  {analysis.composite_risk_score.toFixed(1)}
                </Typography>
                <Chip 
                  label={analysis.severity.toUpperCase()} 
                  color={getSeverityColor(analysis.severity) as any}
                  size="small"
                />
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={analysis.composite_risk_score} 
                color={getRiskScoreColor(analysis.composite_risk_score) as any}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>
                Total Findings
              </Typography>
              <Typography variant="h4">
                {analysis.total_findings}
              </Typography>
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>
                Analysis Period
              </Typography>
              <Typography variant="h4">
                {analysis.analysis_period_days} days
              </Typography>
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>
                Analysis Date
              </Typography>
              <Typography variant="body1">
                {new Date(analysis.analysis_timestamp).toLocaleDateString()}
              </Typography>
            </CardContent>
          </Card>
        </Box>
      </Stack>

      {/* Analysis Modules */}
      <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
        Analysis Modules
      </Typography>

      {/* Behavioral Patterns */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box display="flex" alignItems="center" gap={2} width="100%">
            <Typography variant="subtitle1" fontWeight="bold">
              Behavioral Patterns
            </Typography>
            <Chip 
              size="small"
              label={`Risk: ${analysis.analysis_modules.behavioral.risk_score.toFixed(1)}`}
              color={getRiskScoreColor(analysis.analysis_modules.behavioral.risk_score) as any}
            />
            <Chip 
              size="small"
              label={`${analysis.analysis_modules.behavioral.findings.length} findings`}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          {analysis.analysis_modules.behavioral.findings.length > 0 ? (
            <List>
              {analysis.analysis_modules.behavioral.findings.map((finding, idx) => (
                <React.Fragment key={idx}>
                  <ListItem>
                    <Box width="100%">
                      <Box display="flex" alignItems="center" gap={1} mb={1}>
                        {getSeverityIcon(finding.severity)}
                        <Chip 
                          label={finding.severity.toUpperCase()} 
                          size="small"
                          color={getSeverityColor(finding.severity) as any}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {finding.type.replace(/_/g, ' ').toUpperCase()}
                        </Typography>
                      </Box>
                      <Typography variant="body2" gutterBottom>
                        {finding.description}
                      </Typography>
                      {finding.evidence && (
                        <Paper variant="outlined" sx={{ p: 1, mt: 1, bgcolor: 'grey.50' }}>
                          <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                            {JSON.stringify(finding.evidence, null, 2)}
                          </Typography>
                        </Paper>
                      )}
                    </Box>
                  </ListItem>
                  {idx < analysis.analysis_modules.behavioral.findings.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          ) : (
            <Alert severity="success">No behavioral anomalies detected</Alert>
          )}
        </AccordionDetails>
      </Accordion>

      {/* Capacity Violations */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box display="flex" alignItems="center" gap={2} width="100%">
            <Typography variant="subtitle1" fontWeight="bold">
              Capacity Violations (Queens Case Pattern)
            </Typography>
            <Chip 
              size="small"
              label={`Risk: ${analysis.analysis_modules.capacity_violations.risk_score.toFixed(1)}`}
              color={getRiskScoreColor(analysis.analysis_modules.capacity_violations.risk_score) as any}
            />
            <Chip 
              size="small"
              label={`${analysis.analysis_modules.capacity_violations.findings.length} findings`}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          {analysis.analysis_modules.capacity_violations.findings.length > 0 ? (
            <List>
              {analysis.analysis_modules.capacity_violations.findings.map((finding, idx) => (
                <React.Fragment key={idx}>
                  <ListItem>
                    <Box width="100%">
                      <Box display="flex" alignItems="center" gap={1} mb={1}>
                        {getSeverityIcon(finding.severity)}
                        <Chip 
                          label={finding.severity.toUpperCase()} 
                          size="small"
                          color={getSeverityColor(finding.severity) as any}
                        />
                      </Box>
                      <Typography variant="body2" gutterBottom>
                        {finding.description}
                      </Typography>
                      {finding.evidence?.violations && (
                        <TableContainer component={Paper} variant="outlined" sx={{ mt: 1 }}>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Date</TableCell>
                                <TableCell align="right">Capacity</TableCell>
                                <TableCell align="right">Billed Patients</TableCell>
                                <TableCell align="right">Excess</TableCell>
                                <TableCell align="right">Excess %</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {finding.evidence.violations.slice(0, 5).map((v: any, vidx: number) => (
                                <TableRow key={vidx}>
                                  <TableCell>{v.date}</TableCell>
                                  <TableCell align="right">{v.licensed_capacity}</TableCell>
                                  <TableCell align="right">{v.billed_patients}</TableCell>
                                  <TableCell align="right">{v.excess}</TableCell>
                                  <TableCell align="right">
                                    <Typography color="error" fontWeight="bold">
                                      {v.excess_percentage.toFixed(1)}%
                                    </Typography>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      )}
                    </Box>
                  </ListItem>
                  {idx < analysis.analysis_modules.capacity_violations.findings.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          ) : (
            <Alert severity="success">No capacity violations detected</Alert>
          )}
        </AccordionDetails>
      </Accordion>

      {/* Kickback Indicators */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box display="flex" alignItems="center" gap={2} width="100%">
            <Typography variant="subtitle1" fontWeight="bold">
              Kickback Indicators (Brooklyn Case Pattern)
            </Typography>
            <Chip 
              size="small"
              label={`Risk: ${analysis.analysis_modules.kickback_indicators.risk_score.toFixed(1)}`}
              color={getRiskScoreColor(analysis.analysis_modules.kickback_indicators.risk_score) as any}
            />
            <Chip 
              size="small"
              label={`${analysis.analysis_modules.kickback_indicators.findings.length} findings`}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          {analysis.analysis_modules.kickback_indicators.findings.length > 0 ? (
            <List>
              {analysis.analysis_modules.kickback_indicators.findings.map((finding, idx) => (
                <React.Fragment key={idx}>
                  <ListItem>
                    <Box width="100%">
                      <Box display="flex" alignItems="center" gap={1} mb={1}>
                        {getSeverityIcon(finding.severity)}
                        <Chip 
                          label={finding.severity.toUpperCase()} 
                          size="small"
                          color={getSeverityColor(finding.severity) as any}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {finding.type.replace(/_/g, ' ').toUpperCase()}
                        </Typography>
                      </Box>
                      <Typography variant="body2" gutterBottom>
                        {finding.description}
                      </Typography>
                      {finding.evidence && (
                        <Paper variant="outlined" sx={{ p: 1, mt: 1, bgcolor: 'grey.50' }}>
                          <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                            {JSON.stringify(finding.evidence, null, 2)}
                          </Typography>
                        </Paper>
                      )}
                    </Box>
                  </ListItem>
                  {idx < analysis.analysis_modules.kickback_indicators.findings.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          ) : (
            <Alert severity="success">No kickback indicators detected</Alert>
          )}
        </AccordionDetails>
      </Accordion>

      {analysis.composite_risk_score >= 50 && (
        <Alert severity="warning" sx={{ mt: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            <strong>Whistleblower Note:</strong>
          </Typography>
          <Typography variant="body2">
            This provider has a high composite risk score ({analysis.composite_risk_score.toFixed(1)}). 
            Pattern-of-life analysis suggests patterns similar to recent prosecutions. Consider:
            <ul>
              <li>Documenting timeline of suspicious activities</li>
              <li>Collecting additional evidence of false claims</li>
              <li>Consulting with qui tam counsel</li>
            </ul>
            Remember: Qui tam provisions allow private parties to file lawsuits on behalf of the government 
            and receive up to 30% of recovery.
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

export default PatternOfLifeView;
