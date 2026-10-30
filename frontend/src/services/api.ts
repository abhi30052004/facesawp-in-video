import {
  ApiResponse,
  CreateSwapJobRequest,
  FaceUploadResult,
  HealthCheckResponse,
  StudioUsageStats,
  SwapJobStatusResponse,
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
   * Upload video footage
   */
  async uploadVideo(file: File): Promise<VideoUploadResult> {
    if (this.liveBackendEnabled) {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${this.baseUrl}/videos/upload`, {
        method: 'POST',
        headers: {
          ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }
      const result: ApiResponse<VideoUploadResult> = await response.json();
      return result.data;
    }

    // Local client-side demo representation
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
   * Upload & validate target actor face photo
   */
  async uploadTargetFace(file: File): Promise<FaceUploadResult> {
    if (this.liveBackendEnabled) {
      const formData = new FormData();
      formData.append('image', file);

      const response = await fetch(`${this.baseUrl}/faces/detect`, {
        method: 'POST',
        headers: {
          ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Face analysis failed with status ${response.status}`);
      }
      const result: ApiResponse<FaceUploadResult> = await response.json();
      return result.data;
    }

    // Client-side demo representation
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
}

export const bollySwapApi = new BollySwapApiService();

