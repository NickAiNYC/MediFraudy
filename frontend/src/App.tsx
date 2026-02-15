import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import Layout from './components/Layout/Layout';

// Lazy load pages for better performance
const MasterDashboard = React.lazy(() => import('./pages/MasterDashboard'));
const ProviderDetail = React.lazy(() => import('./pages/ProviderDetail'));
const Settings = React.lazy(() => import('./pages/Settings'));
const Profile = React.lazy(() => import('./pages/Profile'));
const FraudRings = React.lazy(() => import('./pages/FraudRings'));
const Providers = React.lazy(() => import('./pages/Providers'));
const PatternOfLife = React.lazy(() => import('./pages/PatternOfLife'));
const Cases = React.lazy(() => import('./pages/Cases'));
const HomeCarePage = React.lazy(() => import('./pages/HomeCarePage'));
const Alerts = React.lazy(() => import('./pages/Alerts'));
const EvidenceVault = React.lazy(() => import('./pages/EvidenceVault'));

function App() {
  return (
    <Layout>
      <React.Suspense fallback={
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '50vh' 
        }}>
          <CircularProgress sx={{ color: '#10b981' }} />
        </Box>
      }>
        <Routes>
          {/* Redirects */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          
          {/* Main Routes - Everything in one master dashboard */}
          <Route path="/dashboard" element={<MasterDashboard />} />
          <Route path="/provider/:id" element={<ProviderDetail />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/fraud-rings" element={<FraudRings />} />
          <Route path="/providers" element={<Providers />} />
          <Route path="/pattern-of-life" element={<PatternOfLife />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/evidence" element={<EvidenceVault />} />
          <Route path="/home-care" element={<HomeCarePage />} />
          
          {/* 404 Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </React.Suspense>
    </Layout>
  );
}

export default App;
