import React from 'react';
import { RouteObject, Navigate } from 'react-router-dom';

// Lazy load pages
const Providers = React.lazy(() => import('../pages/Providers'));
const ProviderDetail = React.lazy(() => import('../pages/ProviderDetail'));
const Cases = React.lazy(() => import('../pages/Cases'));
const Settings = React.lazy(() => import('../pages/Settings'));
const FraudRings = React.lazy(() => import('../pages/FraudRings'));
const UnifiedDashboard = React.lazy(() => import('../pages/UnifiedDashboard').then(module => ({ default: module.UnifiedDashboard })));
const PatternOfLife = React.lazy(() => import('../pages/PatternOfLife'));
const Profile = React.lazy(() => import('../pages/Profile'));

export const routes: RouteObject[] = [
  {
    path: '/',
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <UnifiedDashboard /> },
      { path: 'providers', element: <Providers /> },
      { path: 'providers/:id', element: <ProviderDetail /> },
      { path: 'fraud-rings', element: <FraudRings /> },
      { path: 'pattern-of-life', element: <PatternOfLife /> },
      { path: 'pattern-of-life/:id', element: <PatternOfLife /> },
      { path: 'cases', element: <Cases /> },
      { path: 'settings', element: <Settings /> },
      { path: 'profile', element: <Profile /> },
    ],
  },
];
