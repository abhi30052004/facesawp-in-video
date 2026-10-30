import { FaceSwapConfiguration, ProjectStatus } from './project';

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  timestamp: string;
}

export interface ApiError {
  errorCode: string;
  message: string;
  field?: string;
  details?: Record<string, unknown>;
}

export interface VideoUploadPayload {
  file: File;
  maxDurationSec?: number;
}

export interface VideoUploadResult {
  fileId: string;
  filename: string;
  storageUrl: string;
  durationSeconds: number;
  width: number;
  height: number;
  fps: number;
  codec: string;
  sizeBytes: number;
}

export interface FaceUploadResult {
  faceId: string;
  previewUrl: string;
  detectedFacesCount: number;
  primaryFaceBoundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  embeddingConfidence: number;
  qualityPassed: boolean;
}

export interface CreateSwapJobRequest {
  projectId?: string;
  title: string;
  sourceVideoId: string;
  targetFaceId: string;
  targetFaceType: 'preset' | 'upload';
  config: FaceSwapConfiguration;
  consentConfirmed: boolean;
}

export interface SwapJobStatusResponse {
  jobId: string;
  projectId: string;
  status: ProjectStatus;
  progressPercent: number;
  currentStage: string;
  currentStageIndex: number;
  totalStages: number;
  etaSeconds: number;
  logChunk: string[];
  error?: string;
  resultUrl?: string;
}

export interface StudioUsageStats {
  creditsRemaining: number;
  creditsTotal: number;
  totalSwapsRendered: number;
  minutesProcessed: number;
  hdExportsRemaining: number;
  storageUsedMb: number;
  storageLimitMb: number;
  currentTier: 'Director VIP' | 'Pro Studio' | 'Indie Creator';
  renewalDate: string;
}

export interface HealthCheckResponse {
  status: 'online' | 'degraded' | 'offline';
  version: string;
  gpuWorkersAvailable: number;
  avgQueueWaitSec: number;
  activeModel: string;
}
