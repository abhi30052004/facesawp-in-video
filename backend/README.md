# BollySwap AI — Backend Foundation, Storage, Face Detection & Real Face Swap Pipeline (Phase 5B)

Studio-grade AI video face-swapping backend for **BollySwap AI**, built with **Python 3.12**, **FastAPI**, **Pydantic v2**, **MongoDB Atlas**, **OpenCV YuNet**, **ONNX Runtime (CPU)**, **FFmpeg**, and **Groq Cloud SDK**.

---

## 🛠️ Architecture & Tech Stack

- **Runtime**: Python 3.12+ (Sequential CPU Inference; CUDA / GPU not required)
- **Web Framework**: FastAPI (Async ASGI)
- **Database**: MongoDB Atlas (`AsyncMongoClient`, PyMongo 4.19+)
- **Face Detection Model**: OpenCV YuNet (`cv2.FaceDetectorYN`) via ONNX Runtime CPU
- **Neural Face-Swap Engine (Phase 5B)**:
  - `LicensedFaceSwapModelAdapter`: Pluggable ONNX Runtime CPU execution provider.
  - Dynamically inspects input nodes, handles NCHW/NHWC tensor layouts, normalizes inputs, executes CPU graph inference, and validates output shapes.
  - `UnconfiguredFaceSwapModelAdapter`: Default honest adapter reporting `model_not_configured` when weights are unconfigured. Strictly prevents mock or fake results.
- **Visual Harmonization & Video Pipeline**:
  - `FaceAligner`: 5-point canonical similarity transformation (ArcFace/InsightFace reference) with inverse re-projection.
  - `create_feathered_mask`: Elliptical mask with Gaussian gradient falloff (`blur_sigma=9.0`) to eliminate harsh perimeter seams.
  - `match_color_stats`: Reinhard LAB color transfer matching lighting temperature, shadows, and skin undertones between source and target faces.
  - `TemporalFaceTracker`: Exponential moving average landmark smoothing across frames to eliminate micro-jitter and interpolate 1-2 frame momentary occlusions.
  - `VideoReader`: Validates media signatures and OpenCV decodability.
  - `FrameSampler`: Sequentially streams frames to avoid memory spikes.
  - `AudioHandler`: Extracts and preserves lossless audio tracks using FFmpeg v7.1.
  - `VideoWriter`: Encodes containers and embeds anti-aliased synthetic media watermark (`BollySwap AI • Synthetic Media`).
  - `VideoProcessingPipeline`: Orchestrates end-to-end lifecycle, per-frame YuNet tracking, swap inference, and job status transitions.
- **Audio & Media**: FFmpeg v7.1 (bundled via `imageio-ffmpeg` or system binary)
- **Storage Layer**: Pluggable storage abstraction (`BaseStorageService` -> `LocalStorageService`, Cloudflare R2 ready)
- **Validation & Settings**: Pydantic v2 & `pydantic-settings`
- **AI Intelligence**: Groq Cloud Python SDK (`groq`)
- **HTTP Client**: HTTPX
- **Test Suite**: Pytest (Focused automated unit and integration tests)

---

## 🎬 Phase 5B Video Processing Pipeline Architecture

```
                       ┌───────────────────────┐
                       │  Uploaded Video MP4   │
                       └──────────┬────────────┘
                                  │
                                  ▼
                        ┌───────────────────┐
                        │   VideoReader     │  <-- Binary container & signature check
                        └─────────┬─────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
       ┌───────────────────┐             ┌───────────────────┐
       │   AudioHandler    │             │   FrameSampler    │
       │ (Lossless AAC/MP4)│             │(Sequential Stream)│
       └─────────┬─────────┘             └─────────┬─────────┘
                 │                                 │
                 │                                 ▼
                 │                       ┌───────────────────┐
                 │                       │  FaceDetector     │  <-- YuNet CPU Detection & Tracking
                 │                       │   (OpenCV Zoo)    │
                 │                       └─────────┬─────────┘
                 │                                 │
                 │                                 ▼
                 │                       ┌───────────────────┐
                 │                       │   FaceAligner     │  <-- 5-Point Canonical Similarity Matrix
                 │                       └─────────┬─────────┘
                 │                                 │
                 │                                 ▼
                 │                       ┌───────────────────┐
                 │                       │   Model Adapter   │  <-- Licensed ONNX Engine (Phase 5B)
                 │                       │(ONNX Runtime CPU) │      (Honest fallback if unconfigured)
                 │                       └─────────┬─────────┘
                 │                                 │
                 │                                 ▼
                 │                       ┌───────────────────┐
                 │                       │  Color Matching & │  <-- Reinhard LAB Color Transfer +
                 │                       │Feathered Blending │      Gaussian Alpha Mask Blending
                 │                       └─────────┬─────────┘
                 │                                 │
                 │                                 ▼
                 │                       ┌───────────────────┐
                 │                       │   VideoWriter     │  <-- Applies Synthetic Media Watermark
                 │                       └─────────┬─────────┘
                 │                                 │
                 └────────────────┬────────────────┘
                                  ▼
                       ┌───────────────────────┐
                       │   AudioHandler Remux  │  <-- Lossless audio stream recombination
                       └──────────┬────────────┘
                                  │
                                  ▼
                       ┌───────────────────────┐
                       │ Output Validation &   │
                       │ Storage Abstraction   │
                       └───────────────────────┘
```

---

## 🔒 Model Licensing Notice & Honest Status Policy

> [!IMPORTANT]
> **Strict Ethical Licensing & Truth-in-AI**:
> Many neural face swap models (such as `inswapper_128.onnx`, SimSwap, or GhostFace) carry non-commercial research restrictions. BollySwap AI strictly respects intellectual property and open-source licenses:
> - **We do not bundle restricted weights without explicit commercial authorization.**
> - **We never fabricate fake inference results, return simulated swaps, or create false completed jobs.**
> - If `FACE_SWAP_ENABLED` is `false` or no model file is configured, the system reports `status: "model_not_configured"` honestly, explaining that the pipeline, YuNet face detection, and tracking are operational and ready for licensed weights.

### How to Configure a Licensed ONNX Face-Swap Model
1. Obtain an authorized ONNX face-replacement model file.
2. Place the `.onnx` model file in `backend/models/` (e.g. `backend/models/my_face_swap.onnx`).
3. In `backend/.env`, set:
   ```env
   FACE_SWAP_ENABLED=true
   FACE_SWAP_MODEL_PATH=models/my_face_swap.onnx
   FACE_SWAP_MODEL_LICENSE=Commercial-Permissive
   FACE_SWAP_PROVIDER=CPUExecutionProvider
   FACE_SWAP_INPUT_SIZE=128
   ```
4. Restart the FastAPI application. The `LicensedFaceSwapModelAdapter` will automatically load the model onto CPUExecutionProvider and process swaps sequentially.

---

## 🗄️ Database Architecture (MongoDB Atlas)

Collections and indexes synchronized on startup:

1. **`users`**: Directorial accounts and studio memberships.
2. **`projects`**:
   - Unique index: `project_id`
   - Indexes: `status`, `created_at` (descending)
   - Fields: `project_id`, `user_id`, `title`, `original_video_id`, `replacement_face_id`, `detected_tracks`, `selected_actor_track_id`, `status`, `created_at`, `updated_at`.
3. **`processing_jobs` & `swap_jobs`**:
   - Unique index: `job_id`
   - Indexes: `project_id`, `status`, `created_at` (descending)
   - Fields: `job_id`, `project_id`, `selected_actor_track_id`, `source_video_id`, `replacement_face_id`, `status` (`queued`, `validating`, `preparing`, `processing`, `finalizing`, `completed`, `failed`, `model_not_configured`), `progress`, `current_step`, `error_message`, `created_at`, `started_at`, `completed_at`, `output_video_id`, `output_video_url`.
4. **`detection_jobs`**:
   - Unique index: `detection_job_id`
   - Indexes: `project_id`, `video_id`, `created_at` (descending)
5. **`consent_records`**:
   - Indexes: `project_id`, `created_at` (descending)
6. **`uploads`**:
   - Unique index: `upload_id`
   - Indexes: `created_at` (descending)

---

## 📡 API Endpoints (Phase 5B)

### Video Processing & Swap Pipeline
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/swaps/create` | Validates assets/consent, checks model readiness, and executes the face-swap video processing pipeline or reports honest `model_not_configured` status. |
| `GET` | `/api/v1/swaps/{job_id}` | Polls processing job status, stage, progress, and error details. |
| `GET` | `/api/v1/swaps/{job_id}/result` | Retrieves output video download URL and render metrics upon completion, or honest unconfigured status. |

### Face Detection & Actor Selection (Phase 4)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/faces/detect` | Triggers real YuNet face detection on source footage; returns tracks & thumbnails |
| `GET` | `/api/v1/faces/detect/{detection_job_id}` | Polls detection job progress, status, and track hypotheses |
| `GET` | `/api/v1/projects/{project_id}/faces` | Retrieves detected actor tracks and active selection for a project |
| `POST` | `/api/v1/projects/{project_id}/faces/select` | Affirms which detected actor track to replace in the swap pipeline |

### System Health & Uploads
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Root system status, version, Groq status, and MongoDB Atlas connectivity |
| `GET` | `/api/v1/health` | Versioned telemetry matching BollySwap frontend contracts |
| `POST` | `/api/v1/videos/upload` | Multipart MP4/MOV video upload (max 100MB), chunked streaming & DB metadata |
| `POST` | `/api/v1/faces/upload` | Multipart JPG/PNG/WEBP face portrait upload (max 10MB) & DB metadata |
| `GET` | `/api/v1/files/{file_id}` | Securely streams stored videos, face portraits, and cropped thumbnails |
| `POST` | `/api/v1/consent` | Records mandatory ethical AI likeness authorization |

---

## 🚀 PowerShell Run Instructions

### 1. Virtual Environment Activation & Installation
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Start Backend Server
```powershell
uvicorn app.main:create_app --factory --reload --port 8000
```
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Interactive ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Run Focused Test Suite
```powershell
.\.venv\Scripts\pytest.exe backend/tests/test_phase5b.py -v
```
