import React, { useState } from 'react';
import { Box, Tabs, Tab, Container, Paper, Button, Typography, Chip } from '@mui/material';
import {
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  WarningAmber as WarningIcon,
  TrendingUp as TrendingIcon,
  HomeWork as HomeWorkIcon,
  Gavel as CaseIcon,
  Download as DownloadIcon,
  Shield as ShieldIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { UnifiedDashboard } from './UnifiedDashboard';
import ProviderSearch from '../components/ProviderSearch';
import FraudRingsPage from './FraudRings';
import PatternOfLife from './PatternOfLife';
import HomeCarePage from './HomeCarePage';
import Cases from './Cases';
import { exportApi } from '../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} id={`tabpanel-${index}`} aria-labelledby={`tab-${index}`} {...other}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

export const MasterDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);

  const handleDownload = () => {
    exportApi.downloadDOJPackage();
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Hero Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <Typography
                variant="h3"
                sx={{
                  fontWeight: 800,
                  background: 'linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  letterSpacing: '-0.025em',
                }}
              >
                Command Center
              </Typography>
              <Chip
                icon={<ShieldIcon sx={{ fontSize: '0.85rem' }} />}
                label="77.3M Claims Analyzed"
                size="small"
                sx={{
                  bgcolor: 'rgba(16, 185, 129, 0.1)',
                  color: '#10b981',
                  fontWeight: 600,
                  fontSize: '0.7rem',
                  fontFamily: '"JetBrains Mono", monospace',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                  '& .MuiChip-icon': { color: '#10b981' },
                }}
              />
            </Box>
            <Typography variant="body1" sx={{ color: '#64748b', fontSize: '0.95rem' }}>
              Unified Multi-Vector Fraud Detection Platform
            </Typography>
          </Box>
          <Button
            variant="contained"
            size="large"
            startIcon={<DownloadIcon />}
            onClick={handleDownload}
            sx={{
              background: 'linear-gradient(135deg, #dc2626 0%, #ef4444 100%)',
              fontWeight: 700,
              px: 3,
              py: 1.5,
              borderRadius: 2,
              boxShadow: '0 4px 15px rgba(239, 68, 68, 0.3)',
              '&:hover': {
                background: 'linear-gradient(135deg, #b91c1c 0%, #dc2626 100%)',
                boxShadow: '0 6px 20px rgba(239, 68, 68, 0.4)',
              },
            }}
          >
            Download DOJ Package
          </Button>
        </Box>
      </motion.div>

      {/* Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <Paper sx={{
          borderBottom: '1px solid #1e293b',
          bgcolor: '#0f172a',
          borderRadius: '12px 12px 0 0',
        }}>
          <Tabs
            value={activeTab}
            onChange={(e, newValue) => setActiveTab(newValue)}
            aria-label="dashboard tabs"
            sx={{
              '& .MuiTab-root': {
                color: '#64748b',
                fontWeight: 500,
                '&.Mui-selected': {
                  color: '#10b981',
                },
              },
              '& .MuiTabs-indicator': {
                backgroundColor: '#10b981',
                height: 3,
                borderRadius: '3px 3px 0 0',
              },
            }}
          >
            <Tab icon={<DashboardIcon />} iconPosition="start" label="Overview" id="tab-0" />
            <Tab icon={<PeopleIcon />} iconPosition="start" label="Providers" id="tab-1" />
            <Tab icon={<WarningIcon />} iconPosition="start" label="Fraud Rings" id="tab-2" />
            <Tab icon={<TrendingIcon />} iconPosition="start" label="Pattern Analysis" id="tab-3" />
            <Tab icon={<HomeWorkIcon />} iconPosition="start" label="Home Care" id="tab-4" />
            <Tab icon={<CaseIcon />} iconPosition="start" label="Cases" id="tab-5" />
          </Tabs>
        </Paper>
      </motion.div>

      <TabPanel value={activeTab} index={0}>
        <UnifiedDashboard />
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <ProviderSearch />
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        <FraudRingsPage />
      </TabPanel>

      <TabPanel value={activeTab} index={3}>
        <PatternOfLife />
      </TabPanel>

      <TabPanel value={activeTab} index={4}>
        <HomeCarePage />
      </TabPanel>

      <TabPanel value={activeTab} index={5}>
        <Cases />
      </TabPanel>
    </Container>
  );
};

export default MasterDashboard;
