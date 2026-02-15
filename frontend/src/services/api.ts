import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// Types
export interface Provider {
  id: number;
  npi: string;
  name: string;
  address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  facility_type?: string;
  specialty?: string;
  licensed_capacity?: number | null;
  created_at?: string;
}

export interface Claim {
  id: number;
  provider_id: number;
  beneficiary_id?: string;
  billing_code: string;
  amount: number;
  claim_date: string;
  submitted_date?: string;
  units?: number;
}

export interface Anomaly {
  id: number;
  provider_id: number;
  billing_code: string;
  z_score: number;
  anomaly_type?: string;
  notes?: string;
  detected_at: string;
}

export interface POLAnalysis {
  composite_risk_score: number;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  analysis_modules: {
    behavioral: { risk_score: number; risk_level: string; findings_count: number };
    capacity_violations: { risk_score: number; risk_level: string; findings_count: number };
    kickback_indicators: { risk_score: number; risk_level: string; findings_count: number };
  };
  all_findings: Array<{
    type: string;
    severity: string;
    description: string;
    evidence?: any;
  }>;
  total_findings: number;
  analysis_timestamp: string;
}

export interface Case {
  id: number;
  case_number: string;
  provider_id: number;
  status: string;
  priority: string;
  description?: string;
  created_at: string;
  updated_at?: string;
}

export interface TimelineEvent {
  id: number;
  case_id: number;
  event_date: string;
  description: string;
  evidence_type?: string;
  created_at: string;
}

export interface SweepResult {
  provider_id: number;
  npi: string;
  name: string;
  city: string;
  facility_type: string;
  risk_score: number;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  findings_count: number;
}

export interface PaginatedResponse<T> {
  providers?: T[];
  anomalies?: T[];
  cases?: T[];
  count: number;
}

// API Client Configuration
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000, // 30 second timeout
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        if (process.env.NODE_ENV === 'development') {
          console.log(`🚀 ${config.method?.toUpperCase()} ${config.url}`, config.params || config.data);
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        if (process.env.NODE_ENV === 'development') {
          console.log(`✅ ${response.status} ${response.config.url}`, response.data);
        }
        return response;
      },
      (error) => {
        if (process.env.NODE_ENV === 'development') {
          console.error('❌ API Error:', error.response?.data || error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  // Generic request wrapper
  async request<T>(config: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.request(config);
    return response.data;
  }

  // Raw axios instance for direct access if needed
  get axiosInstance() {
    return this.client;
  }
}

const api = new ApiClient();

/* --- Graph Analytics --- */
export const graphApi = {
  getFraudRings: (minScore: number = 70) => 
    api.request<any[]>({ url: '/api/graph/fraud-rings', params: { min_score: minScore } }),
  
  getNetworkStats: () => 
    api.request<any>({ url: '/api/graph/network-stats' }),
    
  getProviderNetwork: (providerId: number, depth: number = 2) => 
    api.request<any>({ url: `/api/graph/network/${providerId}`, params: { depth } }),
};

/* --- CDPAP --- */
export const cdpapApi = {
  getNetwork: (limit: number = 100) => 
    api.request<any>({ url: '/api/analytics/cdpap/network', params: { limit } }),
  getImpossibleHours: () => 
    api.request<any[]>({ url: '/api/analytics/cdpap/impossible-hours' }),
};

/* --- Pharmacy --- */
export const pharmacyApi = {
  getLidocaineDumping: (threshold: number = 5000) => 
    api.request<any[]>({ url: '/api/analytics/pharmacy/lidocaine-dumping', params: { threshold } }),
};

/* --- SADC --- */
export const sadcApi = {
  getHeatmap: (limit: number = 1000) => 
    api.request<any[]>({ url: '/api/analytics/sadc/attendance-heatmap', params: { limit } }),
  getSpikes: (threshold: number = 2.5) => 
    api.request<any[]>({ url: '/api/analytics/sadc/attendance-spikes', params: { threshold } }),
};

/* --- Recipient --- */
export const recipientApi = {
  getCardSharingSuspects: (minDist: number = 50) => 
    api.request<any[]>({ url: '/api/analytics/recipient/card-sharing', params: { min_dist: minDist } }),
  getMedicationResellingSuspects: (minPharmacies: number = 3) => 
    api.request<any[]>({ url: '/api/analytics/recipient/reselling-meds', params: { min_pharmacies: minPharmacies } }),
};

/* --- NEMT --- */
export const nemtApi = {
  getGhostRides: (limit: number = 50) => 
    api.request<any[]>({ url: '/api/analytics/nemt/ghost-rides', params: { limit } }),
  getImpossibleTrips: (limit: number = 50) => 
    api.request<any[]>({ url: '/api/analytics/nemt/impossible-trips', params: { limit } }),
};

/* --- Dashboard --- */
export const dashboardApi = {
  getSummary: () => 
    api.request<any>({ url: '/api/analytics/dashboard/summary' }),
};

/* --- Providers --- */
export const providerApi = {
  search: (params: {
    search?: string;
    facility_type?: string;
    state?: string;
    skip?: number;
    limit?: number;
  }) => api.request<PaginatedResponse<Provider>>({
    method: 'GET',
    url: '/api/providers',
    params,
  }),

  get: (id: number) => api.request<Provider>({
    method: 'GET',
    url: `/api/providers/${id}`,
  }),
};

/* --- Anomalies --- */
export const anomalyApi = {
  list: (params: {
    min_z_score?: number;
    billing_code?: string;
    skip?: number;
    limit?: number;
  }) => api.request<PaginatedResponse<Anomaly>>({
    method: 'GET',
    url: '/api/anomalies',
    params,
  }),
};

/* --- Analytics --- */
export const analyticsApi = {
  getBillingStats: (state: string, billingCode?: string) =>
    api.request<any>({
      method: 'GET',
      url: '/api/analytics/stats',
      params: { state, billing_code: billingCode },
    }),

  getOutliers: (zThreshold: number, state: string) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/outliers',
      params: { z_threshold: zThreshold, state },
    }),

  getTrends: (state: string, billingCode?: string) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/trends',
      params: { state, billing_code: billingCode },
    }),

  // --- SADC ---
  getSADCHeatmap: (limit: number = 500) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/sadc/attendance-heatmap',
      params: { limit },
    }),

  getSADCAttendanceSpikes: (threshold: number = 2.5) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/sadc/attendance-spikes',
      params: { threshold },
    }),

  getSADCImpossibleAttendance: () =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/sadc/impossible-attendance',
    }),

  getSADCGhostPatients: () =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/sadc/ghost-patients',
    }),

  // --- CDPAP ---
  getCDPAPSuspiciousCaregivers: (maxPatients: number = 2, minHours: number = 8.0) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/cdpap/suspicious-caregivers',
      params: { max_patients: maxPatients, min_hours: minHours },
    }),

  getCDPAPNetwork: (limit: number = 100) =>
    api.request<any>({
      method: 'GET',
      url: '/api/analytics/cdpap/network',
      params: { limit },
    }),

  getCDPAPImpossibleHours: () =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/cdpap/impossible-hours',
    }),

  // --- Pharmacy ---
  getPharmacyLidocaineDumping: (threshold: number = 5000.0) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/pharmacy/lidocaine-dumping',
      params: { threshold },
    }),

  // --- Recipient ---
  getRecipientCardSharing: (minDistance: number = 50.0) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/recipient/card-sharing',
      params: { min_distance: minDistance },
    }),
    
  getRecipientReselling: (minPharmacies: number = 3) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/recipient/reselling-meds',
      params: { min_pharmacies: minPharmacies },
    }),

  // --- NEMT ---
  getNEMTGhostRides: (limit: number = 50) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/nemt/ghost-rides',
      params: { limit },
    }),
    
  getNEMTImpossibleTrips: (limit: number = 50) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/nemt/impossible-trips',
      params: { limit },
    }),

  compareProvider: (providerId: number) =>
    api.request<any>({
      method: 'GET',
      url: `/api/analytics/compare/${providerId}`,
    }),

  getFraudPatterns: (providerId?: number) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/analytics/fraud-patterns',
      params: { provider_id: providerId },
    }),
};

/* --- Pattern of Life --- */
export const polApi = {
  getFullAnalysis: (providerId: number, lookbackDays: number = 365) =>
    api.request<POLAnalysis>({
      method: 'GET',
      url: `/api/analytics/pattern-of-life/${providerId}`,
      params: { lookback_days: lookbackDays },
    }),

  getSummary: (providerId: number) =>
    api.request<{ risk_score: number; risk_level: string }>({
      method: 'GET',
      url: `/api/analytics/pattern-of-life/${providerId}`,
      params: { summary: true },
    }),

  getBatchSummaries: (providerIds: number[]) =>
    api.request<Record<number, { risk_score: number; risk_level: string }>>({
      method: 'POST',
      url: '/api/analytics/pattern-of-life/batch',
      data: { provider_ids: providerIds },
    }),

  getCapacityViolations: (providerId: number, lookbackDays: number = 365) =>
    api.request<any>({
      method: 'GET',
      url: `/api/analytics/provider/${providerId}/capacity`,
      params: { lookback_days: lookbackDays },
    }),

  getKickbackPatterns: (providerId: number, lookbackDays: number = 365) =>
    api.request<any>({
      method: 'GET',
      url: `/api/analytics/provider/${providerId}/kickbacks`,
      params: { lookback_days: lookbackDays },
    }),

  getBehavioralPatterns: (providerId: number, lookbackDays: number = 365) =>
    api.request<any>({
      method: 'GET',
      url: `/api/analytics/provider/${providerId}/behavioral`,
      params: { lookback_days: lookbackDays },
    }),

  getNYCElderlySweep: (minRiskScore: number = 50, limit: number = 100) =>
    api.request<{ results: SweepResult[]; providers_analyzed: number; high_risk_facilities: number }>({
      method: 'GET',
      url: '/api/analytics/nyc-elderly-care-sweep',
      params: { min_risk_score: minRiskScore, limit },
    }),
};

/* --- Home Care --- */
export const homecareApi = {
  getComprehensiveAnalysis: (providerId: number, lookbackDays: number = 730) =>
    api.request<any>({
      method: 'GET',
      url: `/api/homecare/comprehensive-analysis/${providerId}`,
      params: { lookback_days: lookbackDays },
    }),

  getEVVFraud: (providerId: number, lookbackDays: number = 730) =>
    api.request<any>({
      method: 'GET',
      url: `/api/homecare/evv-fraud/${providerId}`,
      params: { lookback_days: lookbackDays },
    }),

  getHomeboundFraud: (providerId: number, lookbackDays: number = 730) =>
    api.request<any>({
      method: 'GET',
      url: `/api/homecare/homebound-fraud/${providerId}`,
      params: { lookback_days: lookbackDays },
    }),

  getKickbackPatterns: (providerId: number, lookbackDays: number = 730) =>
    api.request<any>({
      method: 'GET',
      url: `/api/homecare/kickback-patterns/${providerId}`,
      params: { lookback_days: lookbackDays },
    }),

  getSweep: (minRiskScore: number = 50, limit: number = 50) =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/homecare/sweep',
      params: { min_risk_score: minRiskScore, limit },
    }),

  getTrendingPatterns: () =>
    api.request<any[]>({
      method: 'GET',
      url: '/api/homecare/trending-patterns',
    }),

  buildFraudCase: (providerId: number) =>
    api.request<any>({
      method: 'GET',
      url: `/api/homecare/case-builder/${providerId}`,
    }),
};

/* --- Cases --- */
export const caseApi = {
  list: (status?: string) =>
    api.request<PaginatedResponse<Case>>({
      method: 'GET',
      url: '/api/cases',
      params: { status },
    }),

  create: (providerId: number, description: string) =>
    api.request<Case>({
      method: 'POST',
      url: '/api/cases',
      params: { provider_id: providerId, description },
    }),

  addTimelineEvent: (
    caseId: number,
    eventDate: string,
    description: string,
    evidenceType: string,
  ) =>
    api.request<TimelineEvent>({
      method: 'POST',
      url: `/api/cases/${caseId}/timeline`,
      params: { event_date: eventDate, description, evidence_type: evidenceType },
    }),
};

/* --- Export --- */
export const exportApi = {
  getProviderReport: (providerId: number) =>
    api.request<any>({
      method: 'GET',
      url: `/api/export/provider/${providerId}`,
    }),

  downloadProviderReport: (providerId: number) => {
    window.open(`${API_BASE}/api/export/provider/${providerId}`, '_blank');
  },

  downloadDOJPackage: () => {
    window.open(`${API_BASE}/api/analytics/export/doj-package`, '_blank');
  },

  downloadCasePackage: (caseId: number, format: 'json' | 'pdf' = 'pdf') => {
    window.open(`${API_BASE}/api/export/case/${caseId}?format=${format}`, '_blank');
  },
};

/* --- Health --- */
export const healthApi = {
  check: () =>
    api.request<{ status: string }>({
      method: 'GET',
      url: '/health',
    }),
};

/* --- DeepSeek Legal Assistant --- */
export const agentApi = {
  chat: (message: string, sessionId: string = 'default', providerId?: number) =>
    api.request<{
      response: string;
      session_id: string;
      model: string;
      configured: boolean;
      error?: boolean;
      usage?: Record<string, number>;
      timestamp?: string;
    }>({
      method: 'POST',
      url: '/api/v1/agent/chat',
      data: {
        message,
        session_id: sessionId,
        provider_id: providerId || null,
      },
    }),

  clearSession: (sessionId: string = 'default') =>
    api.request<{ status: string; session_id: string }>({
      method: 'POST',
      url: `/api/v1/agent/clear-session?session_id=${sessionId}`,
    }),

  getStatus: () =>
    api.request<{ configured: boolean; model: string; description: string }>({
      method: 'GET',
      url: '/api/v1/agent/status',
    }),
};

// Convenience hooks for React (optional but recommended)
export const createApiHooks = () => ({
  useProviders: () => ({
    search: providerApi.search,
    get: providerApi.get,
  }),
  useAnomalies: () => ({
    list: anomalyApi.list,
  }),
  useAnalytics: () => ({
    ...analyticsApi,
  }),
  usePOL: () => ({
    ...polApi,
  }),
  useCases: () => ({
    ...caseApi,
  }),
  useExport: () => ({
    ...exportApi,
  }),
});

// Export all APIs
export const apiService = {
  providers: providerApi,
  anomalies: anomalyApi,
  analytics: analyticsApi,
  pol: polApi,
  cases: caseApi,
  export: exportApi,
  health: healthApi,
  agent: agentApi,
};

// Default export for backward compatibility
const legacyApi = {
  // Providers (legacy)
  searchProviders: providerApi.search,
  getProvider: providerApi.get,
  
  // Anomalies (legacy)
  listAnomalies: anomalyApi.list,
  
  // Analytics (legacy)
  getBillingStats: analyticsApi.getBillingStats,
  getOutliers: analyticsApi.getOutliers,
  getTrends: analyticsApi.getTrends,
  compareProvider: analyticsApi.compareProvider,
  getFraudPatterns: analyticsApi.getFraudPatterns,
  
  // Pattern of Life (legacy)
  getPatternOfLife: polApi.getFullAnalysis,
  getPatternOfLifeSummary: polApi.getSummary,
  getBatchPatternOfLifeSummaries: polApi.getBatchSummaries,
  getCapacityViolations: polApi.getCapacityViolations,
  getKickbackPatterns: polApi.getKickbackPatterns,
  getBehavioralPatterns: polApi.getBehavioralPatterns,
  getNYCElderlySweep: polApi.getNYCElderlySweep,
  
  // Cases (legacy)
  listCases: caseApi.list,
  createCase: caseApi.create,
  addTimelineEvent: caseApi.addTimelineEvent,
  
  // Export (legacy)
  exportProviderReport: exportApi.getProviderReport,
  downloadProviderReport: exportApi.downloadProviderReport,
  downloadCasePackage: exportApi.downloadCasePackage,
  
  // Health
  checkHealth: healthApi.check,
  
  // Service object with all APIs
  apiService,
};

export default legacyApi;
