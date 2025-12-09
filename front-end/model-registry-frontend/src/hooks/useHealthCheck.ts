import { useState, useEffect, useCallback, useRef } from 'react';
import { modelRegistryAPI } from '../services/api';
import type { ApiError } from '../types';

type ComponentHealth = {
  status: string;
  response_time?: number;
  message?: string;
  last_checked?: string;
};

type HealthData = {
  status: string;
  components: Record<string, ComponentHealth>;
  uptime?: number;
  version?: string;
  environment?: string;
  timestamp?: string;
};

type UseHealthCheckReturn = {
  data: HealthData | null;
  loading: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
  lastUpdated: Date | null;
};

/**
 * Custom hook to fetch system health status
 * @param refreshInterval - Auto-refresh interval in milliseconds (null to disable)
 * @returns Health check data, loading state, error, and refetch function
 */
export const useHealthCheck = (refreshInterval: number | null = null): UseHealthCheckReturn => {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const intervalRef = useRef<number | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await modelRegistryAPI.healthCheck();
      setData(response);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError);
      console.error('Health check failed:', apiError);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  // Auto-refresh setup
  useEffect(() => {
    // Clear existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Set up new interval if refreshInterval is provided
    if (refreshInterval !== null && refreshInterval > 0) {
      intervalRef.current = setInterval(() => {
        fetchHealth();
      }, refreshInterval);
    }

    // Cleanup on unmount or when refreshInterval changes
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [refreshInterval, fetchHealth]);

  const refetch = useCallback(async () => {
    await fetchHealth();
  }, [fetchHealth]);

  return {
    data,
    loading,
    error,
    refetch,
    lastUpdated,
  };
};
