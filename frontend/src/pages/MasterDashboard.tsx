import React, { useState } from 'react';
import { Box, Tabs, Tab, Container, Paper, Button } from '@mui/material';
import {
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  WarningAmber as WarningIcon,
  TrendingUp as TrendingIcon,
  HomeWork as HomeWorkIcon,
  Gavel as CaseIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <h1 style={{ margin: '0 0 8px 0', color: '#1a237e' }}>🔍 MediFraudy Command Center</h1>
          <p style={{ margin: 0, color: '#666' }}>Unified Multi-Vector Fraud Detection Platform</p>
        </Box>
        <Button variant="contained" color="error" size="large" startIcon={<DownloadIcon />} onClick={handleDownload}>
          Download DOJ Package
        </Button>
      </Box>

      <Paper sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)} aria-label="dashboard tabs">
          <Tab icon={<DashboardIcon />} iconPosition="start" label="Overview" id="tab-0" />
          <Tab icon={<PeopleIcon />} iconPosition="start" label="Providers" id="tab-1" />
          <Tab icon={<WarningIcon />} iconPosition="start" label="Fraud Rings" id="tab-2" />
          <Tab icon={<TrendingIcon />} iconPosition="start" label="Pattern Analysis" id="tab-3" />
          <Tab icon={<HomeWorkIcon />} iconPosition="start" label="Home Care" id="tab-4" />
          <Tab icon={<CaseIcon />} iconPosition="start" label="Cases" id="tab-5" />
        </Tabs>
      </Paper>

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
