import React from 'react';
import { RouteObject } from 'react-router-dom';

// Lazy load pages
const Dashboard = React.lazy(() => import('../pages/Dashboard'));
const Providers = React.lazy(() => import('../pages/Providers'));
const ProviderDetail = React.lazy(() => import('../pages/ProviderDetail'));
const Analytics = React.lazy(() => import('../pages/Analytics'));
const Cases = React.lazy(() => import('../pages/Cases'));
const Settings = React.lazy(() => import('../pages/Settings'));

export const routes: RouteObject[] = [
  {
    path: '/',
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'providers', element: <Providers /> },
      { path: 'providers/:id', element: <ProviderDetail /> },
      { path: 'analytics', element: <Analytics /> },
      { path: 'cases', element: <Cases /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
];
