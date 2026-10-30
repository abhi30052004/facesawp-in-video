# BollySwap AI — Backend Foundation, Storage & Real AI Face Detection (Phase 4)

Studio-grade AI video face-swapping backend for **BollySwap AI**, built with **Python 3.12**, **FastAPI**, **Pydantic v2**, **MongoDB Atlas**, **OpenCV YuNet**, and **Groq Cloud SDK**.

---

## 🛠️ Architecture & Tech Stack

- **Runtime**: Python 3.12+ (CPU Inference only; CUDA not required)
- **Web Framework**: FastAPI (Async ASGI)
- **Database**: MongoDB Atlas (`AsyncMongoClient`, PyMongo 4.19+)
- **Face Detection Model**: OpenCV YuNet (`cv2.FaceDetectorYN`) via ONNX runtime
- **Video Processing**: OpenCV (`cv2.VideoCapture`, `cv2.VideoWriter`)
- **Storage Layer**: Pluggable storage abstraction (`BaseStorageService` -> `LocalStorageService`, Cloudflare R2 ready)
- **Validation & Settings**: Pydantic v2 & `pydantic-settings`
- **AI Intelligence**: Groq Cloud Python SDK (`groq`)
- **HTTP Client**: HTTPX
- **Test Suite**: Pytest (34 automated unit and integration tests)
- **ASGI Server**: Uvicorn

---

## 🧠 Real AI Face Detection (OpenCV YuNet)

Phase 4 implements real face detection on uploaded videos using OpenCV's official YuNet convolutional detector:

1. **Model Source**:
   - Repository: [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
   - Model File: `backend/models/face_detection_yunet_2023mar.onnx`
   - SHA-256 Checksum: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`
   - License: Apache 2.0 / MIT License (see `backend/models/LICENSE_YUNET.txt`)
2. **Video Frame Extraction (`VideoService`)**:
   - Reads video metadata: width, height, FPS, frame count, duration.
   - Samples frames at configurable temporal intervals (default 1.5s, max 30 frames).
   - Resizes large frames preserving aspect ratio while maintaining memory bounds.
   - Decodes video safely and guarantees resource release via `finally: cap.release()`.
3. **Face Detection (`FaceDetectorYuNet`)**:
   - Runs on CPU dynamically adjusting input size per frame.
   - Extracts bounding boxes `[x, y, w, h]`, 5 facial landmarks (right eye, left eye, nose tip, right mouth corner, left mouth corner), and confidence scores.
   - Filters out detections below configurable threshold (default `0.6`).
   - Crops high-quality face thumbnails with proportional padding and bounds checking.
4. **Actor Track Hypotheses (`FaceTracker`)**:
   - Groups continuous face detections across neighboring sampled frames.
   - Matches candidate tracks using bounding-box Intersection-over-Union (IoU $\ge 0.25$) and temporal proximity ($\le 3.5\text{s}$).
   - Transparently labels candidates as tracking hypotheses (`Actor #1 (Principal Subject)`, `Actor #2`, etc.).
   - No facial recognition embeddings or unverified real-world identity claims.
   - Automatically stores representative face thumbnails to storage abstraction and MongoDB.

---

## 🗄️ Database Architecture (MongoDB Atlas)

Collections and indexes synchronized on startup:

1. **`users`**: Directorial accounts and studio memberships.
2. **`projects`**:
   - Unique index: `project_id`
   - Indexes: `status`, `created_at` (descending)
   - Fields: `project_id`, `user_id`, `title`, `original_video_id`, `replacement_face_id`, `detected_tracks`, `selected_actor_track_id`, `status`, `created_at`, `updated_at`.
3. **`processing_jobs`**:
   - Unique index: `job_id`
   - Indexes: `project_id`, `status`, `created_at` (descending)
4. **`detection_jobs`**:
   - Unique index: `detection_job_id`
   - Indexes: `project_id`, `video_id`, `created_at` (descending)
   - Fields: `detection_job_id`, `project_id`, `video_id`, `detection_status` (`queued`, `extracting_frames`, `detecting_faces`, `grouping_tracks`, `completed`, `failed`), `progress`, `video_metadata`, `sampled_frame_count`, `detected_face_count`, `tracks`, `selected_track_id`.
5. **`consent_records`**:
   - Indexes: `project_id`, `created_at` (descending)
6. **`uploads`**:
   - Unique index: `upload_id`
   - Indexes: `created_at` (descending)
   - Stores metadata for videos, uploaded face portraits, and cropped thumbnails.

---

## 📡 API Endpoints (Phase 4)

### Face Detection & Actor Selection
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/faces/detect` | Triggers real YuNet face detection on source footage; returns tracks & thumbnails |
| `GET` | `/api/v1/faces/detect/{detection_job_id}` | Polls detection job progress, status, and track hypotheses |
| `GET` | `/api/v1/projects/{project_id}/faces` | Retrieves detected actor tracks and active selection for a project |
| `POST` | `/api/v1/projects/{project_id}/faces/select` | Affirms which detected actor track to replace in the swap pipeline |

### System Health
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Root system status, version, Groq status, and MongoDB Atlas connectivity |
| `GET` | `/api/v1/health` | Versioned telemetry matching BollySwap frontend contracts |

### File Uploads & Streaming
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/videos/upload` | Multipart MP4/MOV video upload (max 100MB), chunked streaming & DB metadata |
| `POST` | `/api/v1/faces/upload` | Multipart JPG/PNG/WEBP face portrait upload (max 10MB) & DB metadata |
| `GET` | `/api/v1/files/{file_id}` | Securely streams stored videos, face portraits, and cropped thumbnails |

### Projects & Consent
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/consent` | Records mandatory ethical AI likeness authorization |
| `POST` | `/api/v1/projects` | Creates project in MongoDB and queues an initial job |
| `GET` | `/api/v1/projects` | Lists all projects sorted by creation date |
| `GET` | `/api/v1/projects/{project_id}` | Retrieves project details and associated active job status |
| `GET` | `/api/v1/jobs/{job_id}` | Fetches processing job status, stage, and progress metrics |
| `POST` | `/api/v1/groq/test` | Verifies live Groq inference without exposing API keys |

---

## 🚀 PowerShell Run Instructions

### 1. Virtual Environment Activation & Installation
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Environment Configuration
Verify `backend/.env` contains your parameters:
```env
APP_NAME=BollySwap AI
APP_ENV=development
DEBUG=true
PORT=8000
HOST=0.0.0.0
API_PREFIX=/api/v1
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

# MongoDB Atlas
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.u8obfwb.mongodb.net/
DATABASE_NAME=bollyswap

# Groq Intelligence
GROQ_API_KEY=<your-key>
GROQ_MODEL=qwen/qwen3.8-27b

# Storage & Face Detection
STORAGE_DIR=storage
YUNET_MODEL_PATH=models/face_detection_yunet_2023mar.onnx
FACE_DETECTION_CONFIDENCE_THRESHOLD=0.6
VIDEO_SAMPLE_INTERVAL_SECONDS=1.5
VIDEO_MAX_SAMPLED_FRAMES=30
```

### 3. Start Backend Server
```powershell
uvicorn app.main:create_app --factory --reload --port 8000
```
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Interactive ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 4. Run Test Suite
```powershell
.\.venv\Scripts\pytest.exe backend/tests -v
```

---

## ⚠️ Notes & Limitations

- **CPU Only**: YuNet executes on CPU and does not require NVIDIA CUDA or specialized drivers.
- **Phase 4 Scope**: Focuses strictly on face detection, landmark extraction, and actor track selection.
- **No Face Swapping Yet**: Face replacement, neural blending, and video rendering are scheduled for Phase 5.
- **Hypothesis Grouping**: Track IDs represent continuous spatial/temporal hypotheses and do not claim verified real-world biometric recognition.
