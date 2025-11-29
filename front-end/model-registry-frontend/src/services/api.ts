import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import type {
  IngestResponse,
  SearchResponse,
  Artifact,
  ApiError,
  LogsResponse,
  LogLevel
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 900000, // 15 minute timeout for package ingestion (large models take time)
});

// Token management
export const setAuthToken = (token: string | null) => {
  if (token) {
    apiClient.defaults.headers.common['X-Authorization'] = token;
  } else {
    delete apiClient.defaults.headers.common['X-Authorization'];
  }
};

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ApiError>) => {
    const apiError: ApiError = {
      message: error.response?.data?.message || error.message || 'An error occurred',
      code: error.response?.status?.toString(),
      details: error.response?.data?.details,
    };
    return Promise.reject(apiError);
  }
);

export const modelRegistryAPI = {
  // Authentication
  authenticate: async (username: string, password: string): Promise<{ token: string; calls_remaining: number }> => {
    const response = await apiClient.post('/authenticate', { username, password });
    const { token } = response.data;
    setAuthToken(token);
    return response.data;
  },

  // Ingest package from HuggingFace
  ingestPackage: async (modelId: string, version?: string, description?: string): Promise<IngestResponse> => {
    const payload = {
      model_id: modelId,
      version,
      description
    };
    const response = await apiClient.post<any>('/package/ingest-huggingface', payload);

    // Transform backend response to frontend format
    return {
      id: response.data.package_id,
      name: response.data.name,
      score: response.data.net_score || 0,
      metrics: {
        rampUp: response.data.metrics?.ramp_up_time || 0,
        correctness: response.data.metrics?.code_quality || 0,
        busFactor: response.data.metrics?.bus_factor || 0,
        responsiveMaintainer: response.data.metrics?.reviewedness || 0,
        license: response.data.metrics?.license || 0,
        reviewedness: response.data.metrics?.reviewedness,
        reproducibility: response.data.metrics?.reproducibility,
      },
      status: 'success',
      message: response.data.message
    };
  },

  // Search packages
  searchPackages: async (
    nameQuery?: string,
    version?: string,
    regex?: string,
    offset: number = 0,
    limit: number = 50
  ): Promise<SearchResponse> => {
    const query: any = {};
    if (nameQuery) query.name = nameQuery;
    if (version) query.version = version;
    if (regex) query.regex = regex;

    const response = await apiClient.post<any>('/packages', query, {
      params: { offset, limit }
    });

    // Transform backend response to frontend format
    const page = Math.floor(offset / limit) + 1;
    return {
      artifacts: response.data.packages.map((pkg: any) => ({
        id: pkg.id,
        name: pkg.name,
        version: pkg.version || '1.0.0',
        description: pkg.description || '',
        score: pkg.net_score || 0,
        license: pkg.license,
        createdAt: pkg.upload_date,
        updatedAt: pkg.upload_date,
        metrics: {
          rampUp: 0,
          correctness: 0,
          busFactor: 0,
          responsiveMaintainer: 0,
          license: 0,
        }
      })),
      total: response.data.total,
      page,
      limit
    };
  },

  // Get package by ID
  getPackageById: async (id: string): Promise<Artifact> => {
    const response = await apiClient.get<any>(`/package/${id}/metadata`);

    // Transform backend response to frontend format
    return {
      id: response.data.id,
      name: response.data.name,
      version: response.data.version || '1.0.0',
      description: response.data.description || '',
      score: response.data.metrics?.net_score || 0,
      license: response.data.license,
      createdAt: response.data.upload_date,
      updatedAt: response.data.upload_date,
      metrics: {
        rampUp: response.data.metrics?.ramp_up || 0,
        correctness: response.data.metrics?.code_quality || 0,
        busFactor: response.data.metrics?.bus_factor || 0,
        responsiveMaintainer: response.data.metrics?.reviewedness || 0,
        license: response.data.metrics?.license_score || 0,
        reviewedness: response.data.metrics?.reviewedness,
        reproducibility: response.data.metrics?.reproducibility,
      }
    };
  },

  // Get all packages with pagination
  getAllPackages: async (offset: number = 0, limit: number = 50): Promise<SearchResponse> => {
    return modelRegistryAPI.searchPackages(undefined, undefined, undefined, offset, limit);
  },

  // Download package
  downloadPackage: async (id: string): Promise<{ download_url: string; expires_in_seconds: number }> => {
    const response = await apiClient.get<any>(`/package/${id}`);
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string; components: any }> => {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // Get logs with filtering
  getLogs: async (
    level?: LogLevel,
    source?: string,
    startDate?: string,
    endDate?: string,
    search?: string,
    offset: number = 0,
    limit: number = 100
  ): Promise<LogsResponse> => {
    const params: any = { offset, limit };
    if (level) params.level = level;
    if (source) params.source = source;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (search) params.search = search;

    const response = await apiClient.get<any>('/logs', { params });

    // Transform backend response to frontend format
    const page = Math.floor(offset / limit) + 1;
    return {
      logs: response.data.logs || [],
      total: response.data.total || 0,
      page,
      limit
    };
  },
};

export default apiClient;
