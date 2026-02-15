import { useState } from 'react';
import { polApi } from '../services/api';
import { POLAnalysis } from '../types';

export const usePOLAnalysis = (providerId: number) => {
  const [analysis, setAnalysis] = useState<POLAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async (lookbackDays: number = 365) => {
    setLoading(true);
    setError(null);
    try {
      const result = await polApi.getFullAnalysis(providerId, lookbackDays);
      setAnalysis(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to run analysis');
    } finally {
      setLoading(false);
    }
  };

  return { analysis, loading, error, runAnalysis };
};

export const useNYCSweep = () => {
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSweep = async (minRisk: number = 50, limit: number = 100) => {
    setLoading(true);
    setError(null);
    try {
      const result = await polApi.getNYCElderlySweep(minRisk, limit);
      setResults(result.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to run sweep');
    } finally {
      setLoading(false);
    }
  };

  return { results, loading, error, runSweep };
};