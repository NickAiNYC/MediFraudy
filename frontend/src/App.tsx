import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import Layout from './components/Layout/Layout';

// Lazy load pages for better performance
const MasterDashboard = React.lazy(() => import('./pages/MasterDashboard'));
const Settings = React.lazy(() => import('./pages/Settings'));
const Profile = React.lazy(() => import('./pages/Profile'));

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
          <CircularProgress />
        </Box>
      }>
        <Routes>
          {/* Redirects */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          
          {/* Main Routes - Everything in one master dashboard */}
          <Route path="/dashboard" element={<MasterDashboard />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/profile" element={<Profile />} />
          
          {/* 404 Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </React.Suspense>
    </Layout>
  );
}

export default App;
