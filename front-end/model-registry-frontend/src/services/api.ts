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
    const response = await apiClient.post<unknown>('/package/ingest-huggingface', payload);
    const data = response.data as {
      package_id: string;
      name: string;
      net_score?: number;
      metrics?: Record<string, number>;
      message?: string;
    };

    // Transform backend response to frontend format
    return {
      id: data.package_id,
      name: data.name,
      score: data.net_score || 0,
      metrics: {
        rampUp: data.metrics?.ramp_up_time || 0,
        correctness: data.metrics?.code_quality || 0,
        busFactor: data.metrics?.bus_factor || 0,
        responsiveMaintainer: data.metrics?.reviewedness || 0,
        license: data.metrics?.license || 0,
        reviewedness: data.metrics?.reviewedness,
        reproducibility: data.metrics?.reproducibility,
      },
      status: 'success',
      message: data.message
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
    const query: { name?: string; version?: string; regex?: string } = {};
    if (nameQuery) query.name = nameQuery;
    if (version) query.version = version;
    if (regex) query.regex = regex;

    const response = await apiClient.post<unknown>('/packages', query, {
      params: { offset, limit }
    });
    const data = response.data as {
      packages: unknown[];
      total: number;
    };

    // Transform backend response to frontend format
    const page = Math.floor(offset / limit) + 1;
    return {
      artifacts: data.packages.map((pkg: unknown) => {
        const p = pkg as Record<string, unknown>;
        const metrics = (p.metrics || {}) as Record<string, number | Record<string, number>>;
        return {
          id: p.id as string,
          name: p.name as string,
          version: (p.version as string) || '1.0.0',
          description: (p.description as string) || '',
          score: (p.net_score as number) || 0,
          license: p.license as string,
          createdAt: p.upload_date as string,
          updatedAt: p.upload_date as string,
          metrics: {
            // Phase 1 metrics
            rampUp: (metrics.ramp_up as number) || 0,
            correctness: (metrics.correctness as number) || 0,
            busFactor: (metrics.bus_factor as number) || 0,
            responsiveMaintainer: (metrics.responsive_maintainer as number) || 0,
            license: (metrics.license_score as number) || 0,

            // Phase 2 metrics
            reviewedness: metrics.reviewedness as number | undefined,
            reproducibility: metrics.reproducibility as number | undefined,
            treeScore: metrics.tree_score as number | undefined,
            performanceClaims: metrics.performance_claims as number | undefined,
            datasetQuality: metrics.dataset_quality as number | undefined,
            codeQuality: metrics.code_quality as number | undefined,
            datasetAndCodeScore: metrics.dataset_and_code_score as number | undefined,
            sizeScore: metrics.size_score as number | Record<string, number> | undefined,
          }
        };
      }),
      total: data.total,
      page,
      limit
    };
  },

  // Get package by ID
  getPackageById: async (id: string): Promise<Artifact> => {
    const response = await apiClient.get<unknown>(`/package/${id}/metadata`);
    const p = response.data as Record<string, unknown>;
    const metrics = (p.metrics || {}) as Record<string, number | Record<string, number>>;

    // Transform backend response to frontend format
    return {
      id: p.id as string,
      name: p.name as string,
      version: (p.version as string) || '1.0.0',
      description: (p.description as string) || '',
      score: (metrics.net_score as number) || 0,
      license: p.license as string,
      createdAt: p.upload_date as string,
      updatedAt: p.upload_date as string,
      metrics: {
        // Phase 1 metrics
        rampUp: (metrics.ramp_up as number) || 0,
        correctness: (metrics.correctness as number) || 0,
        busFactor: (metrics.bus_factor as number) || 0,
        responsiveMaintainer: (metrics.responsive_maintainer as number) || 0,
        license: (metrics.license_score as number) || 0,

        // Phase 2 metrics
        reviewedness: metrics.reviewedness as number | undefined,
        reproducibility: metrics.reproducibility as number | undefined,
        treeScore: metrics.tree_score as number | undefined,
        performanceClaims: metrics.performance_claims as number | undefined,
        datasetQuality: metrics.dataset_quality as number | undefined,
        codeQuality: metrics.code_quality as number | undefined,
        datasetAndCodeScore: metrics.dataset_and_code_score as number | undefined,
        sizeScore: metrics.size_score as number | Record<string, number> | undefined,
      }
    };
  },

  // Get all packages with pagination
  getAllPackages: async (offset: number = 0, limit: number = 50): Promise<SearchResponse> => {
    return modelRegistryAPI.searchPackages(undefined, undefined, undefined, offset, limit);
  },

  // Download package
  downloadPackage: async (id: string): Promise<{ download_url: string; expires_in_seconds: number }> => {
    const response = await apiClient.get<unknown>(`/package/${id}`);
    return response.data as { download_url: string; expires_in_seconds: number };
  },

  // Health check
  healthCheck: async (): Promise<{ status: string; components: Record<string, unknown> }> => {
    const response = await apiClient.get<unknown>('/health');
    return response.data as { status: string; components: Record<string, unknown> };
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
    const params: Record<string, string | number> = { offset, limit };
    if (level) params.level = level;
    if (source) params.source = source;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (search) params.search = search;

    const response = await apiClient.get<unknown>('/logs', { params });
    const data = response.data as { logs?: unknown[]; total?: number };

    // Transform backend response to frontend format
    const page = Math.floor(offset / limit) + 1;
    return {
      logs: (data.logs as LogEntry[]) || [],
      total: data.total || 0,
      page,
      limit
    };
  },
};

export default apiClient;
