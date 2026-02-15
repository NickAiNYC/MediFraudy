import { useState, useEffect } from 'react';
import api from '../services/api';
import { Provider, ProviderWithRisk } from '../types';

interface UseProvidersParams {
  search?: string;
  facility_type?: string;
  state?: string;
  page?: number;
  limit?: number;
}

export const useProviders = (params: UseProvidersParams = {}) => {
  const [providers, setProviders] = useState<ProviderWithRisk[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProviders = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.searchProviders({
        search: params.search,
        facility_type: params.facility_type,
        state: params.state,
        skip: ((params.page || 1) - 1) * (params.limit || 50),
        limit: params.limit || 50,
      });
      
      // Cast to ProviderWithRisk[] as the API might return extra fields or we'll enhance it later
      setProviders((response.providers || []) as unknown as ProviderWithRisk[]);
      setTotal(response.count);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch providers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, [params.search, params.facility_type, params.state, params.page]);

  return { providers, total, loading, error, refetch: fetchProviders };
};

export const useProvider = (id: number) => {
  const [provider, setProvider] = useState<Provider | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProvider = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getProvider(id);
      setProvider(response);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch provider');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) fetchProvider();
  }, [id]);

  return { provider, loading, error, refetch: fetchProvider };
};
