import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import Layout from './components/Layout/Layout';

// Lazy load pages for better performance
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Providers = React.lazy(() => import('./pages/Providers'));
const ProviderDetail = React.lazy(() => import('./pages/ProviderDetail'));
const Analytics = React.lazy(() => import('./pages/Analytics'));
const NYCElderlySweep = React.lazy(() => import('./pages/NYCElderlySweep'));
const PatternOfLife = React.lazy(() => import('./pages/PatternOfLife'));
const Cases = React.lazy(() => import('./pages/Cases'));
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
          
          {/* Main Routes */}
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/providers" element={<Providers />} />
          <Route path="/providers/:id" element={<ProviderDetail />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/nyc-sweep" element={<NYCElderlySweep />} />
          <Route path="/pattern-of-life" element={<PatternOfLife />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/profile" element={<Profile />} />
          
          {/* 404 Fallback */}
          <Route path="*" element={
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <h2>404 - Page Not Found</h2>
              <p>The page you're looking for doesn't exist.</p>
            </Box>
          } />
        </Routes>
      </React.Suspense>
    </Layout>
  );
}

export default App;
