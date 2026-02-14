import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

/* --- Providers --- */

export const searchProviders = (params: {
  search?: string;
  facility_type?: string;
  state?: string;
  skip?: number;
  limit?: number;
}) => api.get('/api/providers', { params });

export const getProvider = (id: number) => api.get(`/api/providers/${id}`);

/* --- Anomalies --- */

export const listAnomalies = (params: {
  min_z_score?: number;
  billing_code?: string;
  skip?: number;
  limit?: number;
}) => api.get('/api/anomalies', { params });

/* --- Analytics --- */

export const getBillingStats = (state: string, billingCode?: string) =>
  api.get('/api/analytics/stats', { params: { state, billing_code: billingCode } });

export const getOutliers = (zThreshold: number, state: string) =>
  api.get('/api/analytics/outliers', { params: { z_threshold: zThreshold, state } });

export const getTrends = (state: string, billingCode?: string) =>
  api.get('/api/analytics/trends', { params: { state, billing_code: billingCode } });

export const compareProvider = (providerId: number) =>
  api.get(`/api/analytics/compare/${providerId}`);

export const getFraudPatterns = (providerId?: number) =>
  api.get('/api/analytics/fraud-patterns', { params: { provider_id: providerId } });

/* --- Pattern of Life --- */

export const getPatternOfLife = async (providerId: number, lookbackDays: number = 365) => {
  const response = await api.get(`/api/analytics/pattern-of-life/${providerId}`, {
    params: { lookback_days: lookbackDays }
  });
  return response.data;
};

export const getCapacityViolations = async (providerId: number, lookbackDays: number = 365) => {
  const response = await api.get(`/api/analytics/capacity-violations/${providerId}`, {
    params: { lookback_days: lookbackDays }
  });
  return response.data;
};

export const getKickbackPatterns = async (providerId: number, lookbackDays: number = 365) => {
  const response = await api.get(`/api/analytics/kickback-patterns/${providerId}`, {
    params: { lookback_days: lookbackDays }
  });
  return response.data;
};

export const getBehavioralPatterns = async (providerId: number, lookbackDays: number = 365) => {
  const response = await api.get(`/api/analytics/behavioral-patterns/${providerId}`, {
    params: { lookback_days: lookbackDays }
  });
  return response.data;
};

export const getNYCElderlySweep = async (minRiskScore: number = 50, limit: number = 100) => {
  const response = await api.get('/api/analytics/nyc-elderly-care-sweep', {
    params: { min_risk_score: minRiskScore, limit }
  });
  return response.data;
};

// === NEW: Lightweight summary for search results ===
export const getPatternOfLifeSummary = async (providerId: number) => {
  const response = await api.get(`/api/analytics/pattern-of-life/${providerId}`, {
    params: { summary: true }
  });
  return response.data;
};

// === NEW: Batch summaries for multiple providers ===
export const getBatchPatternOfLifeSummaries = async (providerIds: number[]) => {
  const response = await api.post('/api/analytics/pattern-of-life/batch', {
    provider_ids: providerIds
  });
  return response.data;
};

/* --- Cases --- */

export const listCases = (status?: string) =>
  api.get('/api/cases', { params: { status } });

export const createCase = (caseId: string, facilityId: number, notes: string) =>
  api.post('/api/cases', null, {
    params: { case_id: caseId, facility_id: facilityId, whistleblower_notes: notes },
  });

export const addTimelineEvent = (
  caseId: number,
  eventDate: string,
  description: string,
  evidenceType: string,
) =>
  api.post(`/api/cases/${caseId}/timeline`, null, {
    params: { event_date: eventDate, description, evidence_type: evidenceType },
  });

/* --- Export --- */

export const exportProviderReport = (providerId: number) =>
  api.get(`/api/export/provider/${providerId}`);

// === NEW: Direct download helper ===
export const downloadProviderReport = (providerId: number) => {
  window.open(`${API_BASE}/api/export/provider/${providerId}`, '_blank');
};

// Export as service object
export const apiService = {
  searchProviders,
  getProvider,
  listAnomalies,
  getBillingStats,
  getOutliers,
  getTrends,
  compareProvider,
  getFraudPatterns,
  getPatternOfLife,
  getCapacityViolations,
  getKickbackPatterns,
  getBehavioralPatterns,
  getNYCElderlySweep,
  getPatternOfLifeSummary,      // Added
  getBatchPatternOfLifeSummaries, // Added
  listCases,
  createCase,
  addTimelineEvent,
  exportProviderReport,
  downloadProviderReport,       // Added
};

export default api;
