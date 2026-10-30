import {
  ApiResponse,
  CreateSwapJobRequest,
  FaceDetectionJobResult,
  FaceUploadResult,
  HealthCheckResponse,
  StudioUsageStats,
  SwapJobStatusResponse,
  TrackSelectionResponseData,
  VideoUploadResult,
} from '../types/api';
import { FaceSwapProject } from '../types/project';
import { INITIAL_MOCK_PROJECTS, INITIAL_MOCK_STATS } from './mockData';

const LOCAL_STORAGE_KEY_PROJECTS = 'bollyswap_projects_v1';
const LOCAL_STORAGE_KEY_STATS = 'bollyswap_stats_v1';

class BollySwapApiService {
  private baseUrl: string = 'http://127.0.0.1:8000/api/v1';
  private apiKey: string = '';
  private liveBackendEnabled: boolean = false;

  constructor() {
    this.initStorage();
  }

  public configure(baseUrl: string, apiKey: string, liveBackendEnabled: boolean) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
    this.liveBackendEnabled = liveBackendEnabled;
  }

  private initStorage() {
    if (typeof window === 'undefined') return;
    if (!localStorage.getItem(LOCAL_STORAGE_KEY_PROJECTS)) {
      localStorage.setItem(LOCAL_STORAGE_KEY_PROJECTS, JSON.stringify(INITIAL_MOCK_PROJECTS));
    }
    if (!localStorage.getItem(LOCAL_STORAGE_KEY_STATS)) {
      localStorage.setItem(LOCAL_STORAGE_KEY_STATS, JSON.stringify(INITIAL_MOCK_STATS));
    }
  }

  /**
   * Health check for future FastAPI backend
   */
  async checkBackendHealth(customUrl?: string): Promise<HealthCheckResponse> {
    const targetUrl = customUrl ? customUrl.replace(/\/$/, '') : this.baseUrl;
    try {
      const response = await fetch(`${targetUrl}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
        },
        signal: AbortSignal.timeout(3000),
      });

      if (response.ok) {
        const json: ApiResponse<HealthCheckResponse> = await response.json();
        return json.data;
      }
      throw new Error(`Server responded with ${response.status}`);
    } catch {
      // Graceful offline demo fallback
      return {
        status: 'offline',
        version: '0.1.0-phase1-frontend-demo',
        gpuWorkersAvailable: 0,
        avgQueueWaitSec: 0,
        activeModel: 'BollyMesh-Simulation-Engine',
      };
    }
  }

  /**
   * Upload video footage with real streaming progress
   */
  async uploadVideo(file: File, onProgress?: (percent: number) => void): Promise<VideoUploadResult> {
    if (this.liveBackendEnabled) {
      return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${this.baseUrl}/videos/upload`);

        if (this.apiKey) {
          xhr.setRequestHeader('Authorization', `Bearer ${this.apiKey}`);
        }

        if (xhr.upload && onProgress) {
          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
              const percent = Math.round((event.loaded / event.total) * 100);
              onProgress(percent);
            }
          };
        }

        xhr.onload = () => {
          try {
            const json: ApiResponse<VideoUploadResult> = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300 && json.success) {
              const data = json.data;
              // Ensure storageUrl is absolute for player compatibility
              if (data.storageUrl && !data.storageUrl.startsWith('http') && !data.storageUrl.startsWith('blob:')) {
                const hostBase = this.baseUrl.replace(/\/api\/v1\/?$/, '');
                data.storageUrl = `${hostBase}${data.storageUrl}`;
              }
              resolve(data);
            } else {
              const errMsg = (json as any)?.error?.message || `Video upload failed with status ${xhr.status}`;
              reject(new Error(errMsg));
            }
          } catch (e) {
            reject(new Error(`Failed to parse server upload response (HTTP ${xhr.status})`));
          }
        };

        xhr.onerror = () => {
          reject(new Error('Network error during video upload. Please check backend connection.'));
        };

        xhr.send(formData);
      });
    }

    // Local client-side demo representation with synthetic progress
    if (onProgress) {
      onProgress(30);
      await new Promise((r) => setTimeout(r, 200));
      onProgress(80);
      await new Promise((r) => setTimeout(r, 200));
      onProgress(100);
    }
    const localUrl = URL.createObjectURL(file);
    return {
      fileId: `vid_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      filename: file.name,
      storageUrl: localUrl,
      durationSeconds: 15,
      width: 1920,
      height: 1080,
      fps: 30,
      codec: 'h264',
      sizeBytes: file.size,
    };
  }

  /**
   * Upload & validate target actor face photo with real progress
   */
  async uploadTargetFace(file: File, onProgress?: (percent: number) => void): Promise<FaceUploadResult> {
    if (this.liveBackendEnabled) {
      return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${this.baseUrl}/faces/upload`);

        if (this.apiKey) {
          xhr.setRequestHeader('Authorization', `Bearer ${this.apiKey}`);
        }

        if (xhr.upload && onProgress) {
          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
              const percent = Math.round((event.loaded / event.total) * 100);
              onProgress(percent);
            }
          };
        }

        xhr.onload = () => {
          try {
            const json: ApiResponse<FaceUploadResult> = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300 && json.success) {
              const data = json.data;
              if (data.previewUrl && !data.previewUrl.startsWith('http') && !data.previewUrl.startsWith('blob:')) {
                const hostBase = this.baseUrl.replace(/\/api\/v1\/?$/, '');
                data.previewUrl = `${hostBase}${data.previewUrl}`;
              }
              resolve(data);
            } else {
              const errMsg = (json as any)?.error?.message || `Face upload failed with status ${xhr.status}`;
              reject(new Error(errMsg));
            }
          } catch (e) {
            reject(new Error(`Failed to parse server upload response (HTTP ${xhr.status})`));
          }
        };

        xhr.onerror = () => {
          reject(new Error('Network error during face upload. Please check backend connection.'));
        };

        xhr.send(formData);
      });
    }

    // Client-side demo representation
    if (onProgress) {
      onProgress(40);
      await new Promise((r) => setTimeout(r, 150));
      onProgress(100);
    }
    const localUrl = URL.createObjectURL(file);
    return {
      faceId: `face_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      previewUrl: localUrl,
      detectedFacesCount: 1,
      primaryFaceBoundingBox: {
        x: 120,
        y: 80,
        width: 380,
        height: 440,
      },
      embeddingConfidence: 0.982,
      qualityPassed: true,
    };
  }

  /**
   * Submit likeness consent record
   */
  async recordConsent(payload: {
    projectId: string;
    consentGiven: boolean;
    consentTextVersion?: string;
    affirmation?: string;
  }): Promise<boolean> {
    if (this.liveBackendEnabled) {
      const response = await fetch(`${this.baseUrl}/consent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
        },
        body: JSON.stringify({
          projectId: payload.projectId,
          consentGiven: payload.consentGiven,
          consentTextVersion: payload.consentTextVersion || 'v1.0',
          affirmation: payload.affirmation || 'Likeness consent affirmed for production.',
        }),
      });

      if (!response.ok) {
        const json = await response.json().catch(() => ({}));
        throw new Error(json?.error?.message || 'Failed to record consent record.');
      }
      return true;
    }
    return true;
  }

  /**
   * Create Project in MongoDB
   */
  async createProject(payload: {
    title: string;
    originalVideoId: string;
    replacementFaceId: string;
    userId?: string | null;
    consentConfirmed: boolean;
  }): Promise<any> {
    if (this.liveBackendEnabled) {
      const response = await fetch(`${this.baseUrl}/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
        },
        body: JSON.stringify({
          title: payload.title,
          originalVideoId: payload.originalVideoId,
          replacementFaceId: payload.replacementFaceId,
          userId: payload.userId || null,
          consentConfirmed: payload.consentConfirmed,
        }),
      });

      if (!response.ok) {
        const json = await response.json().catch(() => ({}));
        throw new Error(json?.error?.message || `Project creation failed (HTTP ${response.status})`);
      }
      const result = await response.json();
      return result.data;
    }

    return {
      projectId: `proj_${Date.now()}`,
      title: payload.title,
      status: 'uploaded',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      activeJob: {
        jobId: `job_${Date.now()}`,
        status: 'uploaded',
        progress: 0.0,
        currentStage: 'Asset Ingestion Complete — Awaiting Phase 4 Processing Pipeline',
      },
    };
  }

  /**
   * Submit face swap render job
   */
  async createSwapJob(payload: CreateSwapJobRequest): Promise<SwapJobStatusResponse> {
    if (this.liveBackendEnabled) {
      const response = await fetch(`${this.baseUrl}/swaps/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Job creation failed: status ${response.status}`);
      }
      const result: ApiResponse<SwapJobStatusResponse> = await response.json();
      return result.data;
    }

    // Simulation job contract
    const jobId = `job_${Date.now()}`;
    return {
      jobId,
      projectId: payload.projectId || `proj_${Date.now()}`,
      status: 'processing',
      progressPercent: 5,
      currentStage: 'Footage Ingestion & Frame Extraction',
      currentStageIndex: 1,
      totalStages: 4,
      etaSeconds: 14,
      logChunk: ['Job initialized on BollyMesh GPU cluster node #04'],
    };
  }

  /**
   * Fetch project list from storage or backend
   */
  async getProjects(): Promise<FaceSwapProject[]> {
    if (this.liveBackendEnabled) {
      const response = await fetch(`${this.baseUrl}/projects`, {
        headers: {
          ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
        },
      });
      if (response.ok) {
        const json: ApiResponse<FaceSwapProject[]> = await response.json();
        return json.data;
      }
    }

    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_KEY_PROJECTS);
      if (raw) {
        return JSON.parse(raw);
      }
    } catch {
      // Fallback
    }
    return INITIAL_MOCK_PROJECTS;
  }

  /**
   * Save or update project in client local store
   */
  saveProjectLocally(project: FaceSwapProject): void {
    try {
      const existing = this.getProjectsSync();
      const index = existing.findIndex((p) => p.id === project.id);
      if (index >= 0) {
        existing[index] = project;
      } else {
        existing.unshift(project);
      }
      localStorage.setItem(LOCAL_STORAGE_KEY_PROJECTS, JSON.stringify(existing));
    } catch (e) {
      console.warn('Failed to save project locally', e);
    }
  }

  /**
   * Delete project from client local store
   */
  deleteProjectLocally(projectId: string): void {
    try {
      const existing = this.getProjectsSync().filter((p) => p.id !== projectId);
      localStorage.setItem(LOCAL_STORAGE_KEY_PROJECTS, JSON.stringify(existing));
    } catch (e) {
      console.warn('Failed to delete project locally', e);
    }
  }

  getProjectsSync(): FaceSwapProject[] {
    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_KEY_PROJECTS);
      return raw ? JSON.parse(raw) : INITIAL_MOCK_PROJECTS;
    } catch {
      return INITIAL_MOCK_PROJECTS;
    }
  }

  /**
   * Fetch usage metrics
   */
  async getStudioUsageStats(): Promise<StudioUsageStats> {
    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_KEY_STATS);
      if (raw) return JSON.parse(raw);
    } catch {
      // Ignore
    }
    return INITIAL_MOCK_STATS;
  }

  /**
   * Helper to resolve file URL from upload ID
   */
  getFileUrl(fileId: string): string {
    return `${this.baseUrl}/files/${fileId}`;
  }

  /**
   * Trigger real OpenCV YuNet face detection on video footage
   */
  async detectFaces(projectId: string, videoId: string): Promise<FaceDetectionJobResult> {
    const response = await fetch(`${this.baseUrl}/faces/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
      },
      body: JSON.stringify({ projectId, videoId }),
    });

    if (!response.ok) {
      const json = await response.json().catch(() => ({}));
      throw new Error(json?.error?.message || `Face detection failed with status HTTP ${response.status}`);
    }

    const result: ApiResponse<FaceDetectionJobResult> = await response.json();
    return result.data;
  }

  /**
   * Poll face detection job status
   */
  async getDetectionJob(detectionJobId: string): Promise<FaceDetectionJobResult> {
    const response = await fetch(`${this.baseUrl}/faces/detect/${detectionJobId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
      },
    });

    if (!response.ok) {
      const json = await response.json().catch(() => ({}));
      throw new Error(json?.error?.message || `Failed to fetch detection job (HTTP ${response.status})`);
    }

    const result: ApiResponse<FaceDetectionJobResult> = await response.json();
    return result.data;
  }

  /**
   * Get detected face tracks for project
   */
  async getProjectFaces(projectId: string): Promise<FaceDetectionJobResult> {
    const response = await fetch(`${this.baseUrl}/projects/${projectId}/faces`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
      },
    });

    if (!response.ok) {
      const json = await response.json().catch(() => ({}));
      throw new Error(json?.error?.message || `Failed to fetch project faces (HTTP ${response.status})`);
    }

    const result: ApiResponse<FaceDetectionJobResult> = await response.json();
    return result.data;
  }

  /**
   * Select candidate actor track in the video to replace
   */
  async selectProjectActorTrack(
    projectId: string,
    selectedTrackId: string
  ): Promise<TrackSelectionResponseData> {
    const response = await fetch(`${this.baseUrl}/projects/${projectId}/faces/select`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
      },
      body: JSON.stringify({ selectedTrackId }),
    });

    if (!response.ok) {
      const json = await response.json().catch(() => ({}));
      throw new Error(json?.error?.message || `Track selection failed (HTTP ${response.status})`);
    }

    const result: ApiResponse<TrackSelectionResponseData> = await response.json();
    return result.data;
  }
}

export const bollySwapApi = new BollySwapApiService();

