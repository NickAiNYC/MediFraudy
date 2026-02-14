import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ProviderSearch from './components/ProviderSearch';
import AnomalyTable from './components/AnomalyTable';
import TrendChart from './components/TrendChart';
import CaseManager from './components/CaseManager';
import ProviderDetail from './components/ProviderDetail';
import MapView from './components/MapView';
import ElderlyCareDashboard from './pages/ElderlyCareDashboard';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<ProviderSearch />} />
          <Route path="/anomalies" element={<AnomalyTable />} />
          <Route path="/trends" element={<TrendChart />} />
          <Route path="/cases" element={<CaseManager />} />
          <Route path="/providers/:id" element={<ProviderDetail />} />
          <Route path="/map" element={<MapView />} />
          <Route path="/elderly-care" element={<ElderlyCareDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
