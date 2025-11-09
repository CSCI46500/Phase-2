import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import type { 
  IngestRequest, 
  IngestResponse, 
  SearchResponse, 
  Artifact,
  ApiError 
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for package ingestion
});

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
  // Ingest package from HuggingFace
  ingestPackage: async (modelUrl: string): Promise<IngestResponse> => {
    const payload: IngestRequest = { modelUrl };
    const response = await apiClient.post<IngestResponse>('/package/ingest', payload);
    return response.data;
  },

  // Search artifacts by regex pattern
  searchByRegex: async (
    regex: string, 
    page: number = 1, 
    limit: number = 20
  ): Promise<SearchResponse> => {
    const response = await apiClient.get<SearchResponse>('/artifacts/byRegex', {
      params: { regex, page, limit },
    });
    return response.data;
  },

  // Get artifact by ID
  getArtifactById: async (id: string): Promise<Artifact> => {
    const response = await apiClient.get<Artifact>(`/artifacts/id/${id}`);
    return response.data;
  },

  // Get all artifacts with pagination
  getAllArtifacts: async (page: number = 1, limit: number = 20): Promise<SearchResponse> => {
    const response = await apiClient.get<SearchResponse>('/artifacts', {
      params: { page, limit },
    });
    return response.data;
  },

  // Download artifact (future implementation)
  downloadArtifact: async (id: string): Promise<Blob> => {
    const response = await apiClient.get<Blob>(`/artifacts/${id}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export default apiClient;
