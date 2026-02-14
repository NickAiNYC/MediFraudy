// Provider types
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

export interface ProviderWithRisk extends Provider {
  risk_score?: number;
  risk_level?: 'HIGH' | 'MEDIUM' | 'LOW';
}

// Claim types
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

// Anomaly types
export interface Anomaly {
  id: number;
  provider_id: number;
  billing_code: string;
  z_score: number;
  anomaly_type?: string;
  notes?: string;
  detected_at: string;
}

// Pattern of Life types
export interface POLIndicator {
  score: number;
  details: string;
  [key: string]: any;
}

export interface POLAnalysis {
  provider_id: number;
  provider_name: string;
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

// Case types
export interface Case {
  id: number;
  case_id: string;
  provider_id: number;
  status: 'open' | 'under_seal' | 'filed' | 'settled';
  whistleblower_notes?: string;
  evidence_summary?: string;
  created_at: string;
  updated_at: string;
}

export interface TimelineEvent {
  id: number;
  case_id: number;
  event_date: string;
  description: string;
  evidence_type?: string;
  created_at: string;
}

// API response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

export interface ApiError {
  detail: string;
  status: number;
}
