export type ProjectStatus = 'draft' | 'processing' | 'completed' | 'failed';

export type VideoFormat = 'mp4' | 'mov' | 'webm';

export interface VideoMetadata {
  name: string;
  url: string;
  sizeBytes: number;
  durationSec: number;
  width: number;
  height: number;
  fps?: number;
  format: VideoFormat;
  isDemoSample?: boolean;
  uploadId?: string;
}

export interface TargetFacePreset {
  id: string;
  name: string;
  title: string;
  category: 'Cinematic Legends' | 'Action Heroes' | 'Romantic Era' | 'Contemporary Stars';
  era: string;
  avatarUrl: string;
  description: string;
  filmReference: string;
  suitabilityScore: number;
  isDemo: true;
}

export interface TargetFaceSelection {
  type: 'custom' | 'preset';
  id?: string;
  name: string;
  previewUrl: string;
  isDemo: boolean;
  detectedLandmarksCount?: number;
  qualityRating?: 'Excellent' | 'Good' | 'Fair';
}

export interface ProcessingLogEntry {
  timestamp: string;
  message: string;
  stageId: number;
  status: 'pending' | 'running' | 'completed' | 'warning';
}

export interface ProcessingPipelineStage {
  id: number;
  title: string;
  subtitle: string;
  detail: string;
  durationMs: number;
}

export interface ProcessingState {
  currentStageIndex: number;
  progress: number; // 0 to 100
  elapsedSeconds: number;
  estimatedRemainingSeconds: number;
  logs: ProcessingLogEntry[];
  currentMetric: {
    label: string;
    value: string;
  };
  isDemoSimulated: true;
}

export interface RenderResult {
  outputVideoUrl: string;
  originalVideoUrl: string;
  swappedFacePreviewUrl: string;
  resolution: string;
  renderDurationSec: number;
  framesProcessed: number;
  fps: number;
  modelIdentifier: string;
  isDemoSimulation: true;
  watermarked: boolean;
  checksum: string;
}

export interface FaceSwapConfiguration {
  faceEnhance: boolean;
  colorHarmony: boolean;
  temporalConsistency: boolean;
  resolutionTarget: '720p' | '1080p' | '4k';
  cinematicGrade: 'authentic' | 'warm-vintage' | 'vibrant-masala' | 'moody-noir';
  watermarkEnabled: boolean;
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

export interface FaceSwapProject {
  id: string;
  title: string;
  description?: string;
  status: ProjectStatus;
  createdAt: string;
  updatedAt: string;
  sourceVideo?: VideoMetadata;
  targetFace?: TargetFaceSelection;
  detectedTracks?: DetectedActorTrack[];
  selectedActorTrackId?: string;
  configuration: FaceSwapConfiguration;
  consentGranted: boolean;
  consentTimestamp?: string;
  result?: RenderResult;
}

