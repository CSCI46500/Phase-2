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
    // Backend expects AuthenticationRequest format: { user: { name, is_admin }, secret: { password } }
    const authRequest = {
      user: {
        name: username,
        is_admin: false  // Will be determined by backend based on credentials
      },
      secret: {
        password: password
      }
    };
    const response = await apiClient.post('/authenticate', authRequest);
    // Backend returns "bearer <token>" string
    const tokenString = typeof response.data === 'string' ? response.data : response.data.token;
    const token = tokenString.replace('bearer ', '');
    setAuthToken(token);
    return { token, calls_remaining: 1000 };
  },

  // Ingest package from HuggingFace
  ingestPackage: async (modelId: string, _version?: string, description?: string): Promise<IngestResponse> => {  // _version unused but kept for API compatibility
    // Convert model_id to HuggingFace URL format
    // modelId can be like "google-bert/bert-base-uncased" or a full URL
    let url = modelId;
    if (!modelId.startsWith('http')) {
      url = `https://huggingface.co/${modelId}`;
    }

    // Backend expects ArtifactData: { url, name?, download_url? }
    const payload = {
      url: url,
      name: description  // Use description as custom name if provided
    };

    // Use the Phase 2 artifact endpoint
    const response = await apiClient.post<any>('/artifact/model', payload);

    // Transform backend response (Artifact format) to frontend format
    return {
      id: response.data.metadata?.id || response.data.package_id,
      name: response.data.metadata?.name || response.data.name,
      score: 0,  // Score retrieved separately via /artifact/model/{id}/rate
      metrics: {
        rampUp: 0,
        correctness: 0,
        busFactor: 0,
        responsiveMaintainer: 0,
        license: 0,
      },
      status: 'success',
      message: 'Model artifact created successfully'
    };
  },

  // Search packages (artifacts)
  searchPackages: async (
    nameQuery?: string,
    _version?: string,  // Unused but kept for API compatibility
    regex?: string,
    offset: number = 0,
    limit: number = 50
  ): Promise<SearchResponse> => {
    // Phase 2 API uses /artifacts endpoint with ArtifactQuery list
    // or /artifact/byRegEx for regex search
    if (regex) {
      // Use regex search endpoint
      const response = await apiClient.post<any>('/artifact/byRegEx', { regex });
      const page = Math.floor(offset / limit) + 1;
      return {
        artifacts: (Array.isArray(response.data) ? response.data : []).map((artifact: any) => ({
          id: artifact.id,
          name: artifact.name,
          version: artifact.type || 'model',
          description: '',
          score: 0,
          license: '',
          createdAt: '',
          updatedAt: '',
          metrics: { rampUp: 0, correctness: 0, busFactor: 0, responsiveMaintainer: 0, license: 0 }
        })),
        total: Array.isArray(response.data) ? response.data.length : 0,
        page,
        limit
      };
    }

    // Use /artifacts endpoint for general search
    const queries = nameQuery
      ? [{ name: nameQuery, types: null }]
      : [{ name: '*', types: null }];

    const response = await apiClient.post<any>('/artifacts', queries, {
      params: { offset: offset.toString() }
    });

    // Transform backend response (list of ArtifactMetadata) to frontend format
    const page = Math.floor(offset / limit) + 1;
    const artifacts = Array.isArray(response.data) ? response.data : [];
    return {
      artifacts: artifacts.map((artifact: any) => ({
        id: artifact.id,
        name: artifact.name,
        version: artifact.type || 'model',
        description: '',
        score: 0,
        license: '',
        createdAt: '',
        updatedAt: '',
        metrics: { rampUp: 0, correctness: 0, busFactor: 0, responsiveMaintainer: 0, license: 0 }
      })),
      total: artifacts.length,
      page,
      limit
    };
  },

  // Get package by ID (artifact type defaults to 'model')
  getPackageById: async (id: string, artifactType: string = 'model'): Promise<Artifact> => {
    // Phase 2 API: /artifacts/{artifact_type}/{id}
    const response = await apiClient.get<any>(`/artifacts/${artifactType}/${id}`);

    // Also get rating if available
    let metrics: any = {};
    try {
      const ratingResponse = await apiClient.get<any>(`/artifact/model/${id}/rate`);
      metrics = {
        rampUp: ratingResponse.data.ramp_up_time || 0,
        correctness: ratingResponse.data.code_quality || 0,
        busFactor: ratingResponse.data.bus_factor || 0,
        responsiveMaintainer: ratingResponse.data.reviewedness || 0,
        license: ratingResponse.data.license || 0,
        reviewedness: ratingResponse.data.reviewedness,
        reproducibility: ratingResponse.data.reproducibility,
        treeScore: ratingResponse.data.tree_score,
        performanceClaims: ratingResponse.data.performance_claims,
        datasetQuality: ratingResponse.data.dataset_quality,
        codeQuality: ratingResponse.data.code_quality,
        datasetAndCodeScore: ratingResponse.data.dataset_and_code_score,
        sizeScore: ratingResponse.data.size_score,
      };
    } catch {
      // Rating not available
    }

    // Transform backend Artifact response to frontend format
    // Ensure metrics has all required fields
    const fullMetrics = {
      rampUp: metrics.rampUp || 0,
      correctness: metrics.correctness || 0,
      busFactor: metrics.busFactor || 0,
      responsiveMaintainer: metrics.responsiveMaintainer || 0,
      license: metrics.license || 0,
      ...metrics
    };
    return {
      id: response.data.metadata?.id || id,
      name: response.data.metadata?.name || '',
      version: response.data.metadata?.type || artifactType,
      description: '',
      score: fullMetrics.license || 0,
      license: '',
      createdAt: '',
      updatedAt: '',
      downloadUrl: response.data.data?.download_url,
      metrics: fullMetrics
    };
  },

  // Get all packages with pagination
  getAllPackages: async (offset: number = 0, limit: number = 50): Promise<SearchResponse> => {
    return modelRegistryAPI.searchPackages(undefined, undefined, undefined, offset, limit);
  },

  // Download package (get artifact with download URL)
  downloadPackage: async (id: string, artifactType: string = 'model'): Promise<{ download_url: string; expires_in_seconds: number }> => {
    // Phase 2 API: /artifacts/{artifact_type}/{id}
    const response = await apiClient.get<any>(`/artifacts/${artifactType}/${id}`);
    return {
      download_url: response.data.data?.download_url || '',
      expires_in_seconds: 3600
    };
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
