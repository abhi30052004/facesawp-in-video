import { FaceSwapProject, ProcessingPipelineStage, TargetFacePreset, VideoMetadata } from '../types/project';
import { StudioUsageStats } from '../types/api';
import { StudioSettings } from '../types/settings';

// Target face presets (empty by default; user uploads authentic target faces)
export const DEMO_ACTOR_PRESETS: TargetFacePreset[] = [];

// Sample demo videos (empty; user uploads authentic source video footage)
export const DEMO_SAMPLE_VIDEOS: VideoMetadata[] = [];

export const DEMO_PIPELINE_STAGES: ProcessingPipelineStage[] = [
  {
    id: 1,
    title: 'Footage Ingestion & Frame Extraction',
    subtitle: 'Decoding video frames and caching timestamps',
    detail: 'Isolating 30fps frames, assessing motion vectors, and detecting camera pan shifts.',
    durationMs: 3200,
  },
  {
    id: 2,
    title: '3D Facial Mesh & Landmark Tracking',
    subtitle: 'Mapping 468 facial anchor points',
    detail: 'Tracking facial orientation, eye-gaze trajectories, expression dynamics, and lighting occlusion vectors.',
    durationMs: 3800,
  },
  {
    id: 3,
    title: 'Neural Latent Swapping & Lighting Blending',
    subtitle: 'Projecting identity embedding onto source frames',
    detail: 'Matching ambient studio temperature, skin undertones, subsurface scattering, and shadow boundaries.',
    durationMs: 4200,
  },
  {
    id: 4,
    title: 'Temporal Consistency & Audio Remuxing',
    subtitle: 'Stabilizing jitter and finalizing export container',
    detail: 'Eliminating inter-frame flickering, preserving natural hair edges, and syncing high-fidelity stereo audio.',
    durationMs: 2800,
  },
];

export const INITIAL_MOCK_STATS: StudioUsageStats = {
  creditsRemaining: 100,
  creditsTotal: 100,
  totalSwapsRendered: 0,
  minutesProcessed: 0,
  hdExportsRemaining: 10,
  storageUsedMb: 0,
  storageLimitMb: 10000,
  currentTier: 'Pro Studio',
  renewalDate: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
};

// Clean initial projects archive (no fake or placeholder items)
export const INITIAL_MOCK_PROJECTS: FaceSwapProject[] = [];

export const INITIAL_STUDIO_SETTINGS: StudioSettings = {
  profile: {
    name: 'Studio Director',
    email: 'studio@bollyswap.ai',
    role: 'VFX Director',
    studioName: 'BollySwap AI Studio',
    avatarUrl: '',
    memberSince: '2026',
  },
  preferences: {
    defaultResolution: '1080p',
    autoFaceEnhance: true,
    colorGradingDefault: 'authentic',
    watermarkPlacement: 'bottom-right',
    audioPassthrough: true,
    sendNotificationOnComplete: true,
    retentionDays: 30,
  },
  apiConfig: {
    backendUrl: 'http://127.0.0.1:8001/api/v1',
    apiKey: '',
    useLiveBackend: true,
    connectionStatus: 'connected',
    lastPingMs: 0,
  },
};
