export interface UserProfile {
  name: string;
  email: string;
  role: string;
  studioName: string;
  avatarUrl: string;
  memberSince: string;
}

export interface StudioAiPreferences {
  defaultResolution: '720p' | '1080p' | '4k';
  autoFaceEnhance: boolean;
  colorGradingDefault: 'authentic' | 'warm-vintage' | 'vibrant-masala' | 'moody-noir';
  watermarkPlacement: 'bottom-right' | 'bottom-left' | 'none';
  audioPassthrough: boolean;
  sendNotificationOnComplete: boolean;
  retentionDays: number;
}

export interface ApiConnectionConfig {
  backendUrl: string;
  apiKey: string;
  useLiveBackend: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'testing' | 'offline_demo';
  lastPingMs?: number;
}

export interface StudioSettings {
  profile: UserProfile;
  preferences: StudioAiPreferences;
  apiConfig: ApiConnectionConfig;
}

