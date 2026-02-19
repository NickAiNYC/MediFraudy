import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  IconButton,
  Badge,
  Collapse,
  Alert,
  AlertTitle,
  Stack,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import {
  NotificationsActive,
  Warning,
  Error,
  Info,
  ExpandMore,
  ExpandLess,
  TrendingUp,
  AccountBalance,
  LocalHospital,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import CountUp from 'react-countup';

interface FraudAlert {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  type: string;
  provider: string;
  amount: number;
  timestamp: Date;
  description: string;
  riskScore: number;
}

export const RealTimeFraudAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<FraudAlert[]>([]);
  const [expanded, setExpanded] = useState(true);
  const [newAlertCount, setNewAlertCount] = useState(0);

  // Fetch real alerts from API
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await fetch('/api/alerts?limit=10');
        if (response.ok) {
          const data = await response.json();
          const formattedAlerts: FraudAlert[] = data.alerts?.map((alert: any) => ({
            id: alert.id?.toString() || Math.random().toString(36),
            severity: alert.severity || 'medium',
            type: alert.anomaly_type || 'Unknown',
            provider: alert.provider_name || `Provider ${alert.provider_id}`,
            amount: alert.amount || 0,
            timestamp: new Date(alert.detected_at || Date.now()),
            description: alert.description || 'Anomalous pattern detected',
            riskScore: alert.risk_score || 0,
          })) || [];
          
          if (formattedAlerts.length > 0) {
            setAlerts(formattedAlerts);
            setNewAlertCount(formattedAlerts.length);
          }
        }
      } catch (error) {
        console.error('Failed to fetch alerts:', error);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#dc2626';
      case 'high': return '#f59e0b';
      case 'medium': return '#3b82f6';
      case 'low': return '#64748b';
      default: return '#64748b';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <Error />;
      case 'high': return <Warning />;
      default: return <Info />;
    }
  };

  return (
    <Card
      sx={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        border: '1px solid #334155',
        position: 'relative',
        overflow: 'visible',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Badge badgeContent={newAlertCount} color="error" max={99}>
              <NotificationsActive sx={{ color: '#ef4444', fontSize: 28 }} />
            </Badge>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Real-Time Fraud Alerts
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748b' }}>
                Live monitoring • Updated every 15s
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={() => setExpanded(!expanded)} size="small">
            {expanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          <Stack spacing={2}>
            <AnimatePresence>
              {alerts.slice(0, 5).map((alert, index) => (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, x: -20, scale: 0.95 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, x: 20, scale: 0.95 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <Alert
                    severity={alert.severity === 'critical' || alert.severity === 'high' ? 'error' : 'warning'}
                    icon={getSeverityIcon(alert.severity)}
                    sx={{
                      bgcolor: `${getSeverityColor(alert.severity)}15`,
                      border: `1px solid ${getSeverityColor(alert.severity)}40`,
                      '& .MuiAlert-icon': {
                        color: getSeverityColor(alert.severity),
                      },
                    }}
                  >
                    <AlertTitle sx={{ fontWeight: 700, fontSize: '0.9rem' }}>
                      {alert.type} • {alert.provider}
                    </AlertTitle>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                      <Typography variant="body2" sx={{ color: '#94a3b8' }}>
                        ${alert.amount.toLocaleString()} • Risk Score: {alert.riskScore}
                      </Typography>
                      <Chip
                        label={alert.severity.toUpperCase()}
                        size="small"
                        sx={{
                          bgcolor: getSeverityColor(alert.severity),
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.65rem',
                        }}
                      />
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={alert.riskScore}
                      sx={{
                        mt: 1,
                        height: 4,
                        borderRadius: 2,
                        bgcolor: '#1e293b',
                        '& .MuiLinearProgress-bar': {
                          bgcolor: getSeverityColor(alert.severity),
                        },
                      }}
                    />
                  </Alert>
                </motion.div>
              ))}
            </AnimatePresence>

            {alerts.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body2" sx={{ color: '#64748b' }}>
                  No active alerts. System monitoring...
                </Typography>
              </Box>
            )}
          </Stack>
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default RealTimeFraudAlerts;
