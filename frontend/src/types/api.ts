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
  databaseConnected?: boolean;
  databaseStatus?: string;
  databaseName?: string;
}

export interface ProjectCreatePayload {
  title: string;
  originalVideoId: string;
  replacementFaceId: string;
  userId?: string | null;
  consentConfirmed: boolean;
}

export interface ProjectCreateResult {
  projectId: string;
  userId?: string | null;
  title: string;
  originalVideoId: string;
  replacementFaceId: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  activeJob?: {
    jobId: string;
    projectId: string;
    status: string;
    progress: number;
    currentStage: string;
    errorMessage?: string | null;
    createdAt: string;
    updatedAt: string;
  };
}

export interface ConsentPayload {
  projectId: string;
  consentGiven: boolean;
  consentTextVersion?: string;
  affirmation?: string;
}

export interface ConsentResult {
  consentId: string;
  projectId: string;
  consentGiven: boolean;
  consentTextVersion: string;
  affirmation: string;
  createdAt: string;
}

export interface DetectedActorTrack {
  trackId: string;
  label: string;
  confidence: number;
  thumbnailFileId: string;
  thumbnailUrl: string;
  occurrences: number;
  timestamps: number[];
  boundingBox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  landmarks?: number[][];
}

export interface FaceDetectionJobResult {
  detectionJobId: string;
  projectId: string;
  videoId: string;
  detectionStatus: 'queued' | 'extracting_frames' | 'detecting_faces' | 'grouping_tracks' | 'completed' | 'failed';
  progress: number;
  currentStage: string;
  videoMetadata?: {
    width: number;
    height: number;
    fps: number;
    durationSeconds: number;
    frameCount: number;
  };
  sampledFrameCount: number;
  detectedFaceCount: number;
  tracks: DetectedActorTrack[];
  selectedTrackId?: string;
  errorMessage?: string | null;
  createdAt: string;
  completedAt?: string | null;
}

export interface TrackSelectionResponseData {
  projectId: string;
  selectedTrackId: string;
  selectedTrack?: DetectedActorTrack;
  message: string;
}
