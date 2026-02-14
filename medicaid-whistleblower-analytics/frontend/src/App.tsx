import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import Layout from './components/Layout/Layout';

// Lazy load pages for better performance
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Providers = React.lazy(() => import('./pages/Providers'));
const ProviderDetail = React.lazy(() => import('./pages/ProviderDetail'));
const Analytics = React.lazy(() => import('./pages/Analytics'));
const Cases = React.lazy(() => import('./pages/Cases'));
const Settings = React.lazy(() => import('./pages/Settings'));

function App() {
  return (
    <Layout>
      <React.Suspense fallback={
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      }>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/providers" element={<Providers />} />
          <Route path="/providers/:id" element={<ProviderDetail />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </React.Suspense>
    </Layout>
  );
}

export default App;
