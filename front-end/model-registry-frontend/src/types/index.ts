// Using types for internal components (recommended for private codebases)
export type ModelMetrics = {
  // Phase 1 metrics
  rampUp: number;
  correctness: number;
  busFactor: number;
  responsiveMaintainer: number;
  license: number;

  // Phase 2 metrics
  reviewedness?: number;
  reproducibility?: number;
  treeScore?: number;
  performanceClaims?: number;
  datasetQuality?: number;
  codeQuality?: number;
  datasetAndCodeScore?: number;
  sizeScore?: number | { raspberry_pi?: number; jetson_nano?: number; desktop_pc?: number; aws_server?: number };
};

export type Artifact = {
  id: string;
  name: string;
  description: string;
  score: number;
  metrics: ModelMetrics;
  version?: string;
  license?: string;
  author?: string;
  createdAt: string;
  updatedAt: string;
  lineage?: string[];
  downloadUrl?: string;
};

export type IngestRequest = {
  modelUrl: string;
};

export type IngestResponse = {
  id: string;
  name: string;
  score: number;
  metrics: ModelMetrics;
  status: 'success' | 'failed';
  message?: string;
};

export type SearchResponse = {
  artifacts: Artifact[];
  total: number;
  page: number;
  limit: number;
};

export type ApiError = {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
};

export type SearchType = 'regex' | 'id' | 'all';

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

export type LogEntry = {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  source?: string;
  user?: string;
  metadata?: Record<string, unknown>;
};

export type LogsResponse = {
  logs: LogEntry[];
  total: number;
  page: number;
  limit: number;
};
