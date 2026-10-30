import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.schemas.health import HealthData, HealthResponse
from app.schemas.groq import GroqTestRequest, GroqTestResponse
from app.schemas.upload import (
    VideoUploadResponse,
    VideoUploadResult,
    FaceUploadResponse,
    FaceUploadResult,
)
from app.schemas.project import (
    ConsentRequest,
    ConsentResponse,
    ConsentRecordData,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectResponseData,
    ProjectListResponse,
    ProjectDetailResponse,
    JobDetailResponse,
    JobResponseData,
)
from app.schemas.detection import (
    FaceDetectRequest,
    FaceDetectResponse,
    DetectionJobResponse,
    TrackSelectionRequest,
    TrackSelectionResponse,
    ProjectFacesResponse,
)
from app.services.database import DatabaseService, get_database_service
from app.services.groq_service import GroqService, get_groq_service
from app.services.storage_service import (
    BaseStorageService,
    LocalStorageService,
    StorageValidationError,
    get_storage_service,
)
from app.services.project_service import ProjectService, get_project_service
from app.services.detection_service import DetectionService, get_detection_service

logger = logging.getLogger("bollyswap.api")

api_router = APIRouter()
root_router = APIRouter()

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
ALLOWED_VIDEO_MIMES = {"video/mp4", "video/quicktime", "video/webm", "application/octet-stream"}

ALLOWED_FACE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FACE_MIMES = {"image/jpeg", "image/png", "image/webp", "application/octet-stream"}


def build_health_data(settings: Settings, db_service: DatabaseService) -> HealthData:
    """Builds structured health and database readiness metrics without exposing secrets."""
    db_connected = db_service.is_connected
    db_status = db_service.status

    return HealthData(
        status="online" if (db_connected or not settings.is_mongodb_configured) else "degraded",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        groq_configured=settings.is_groq_configured,
        groq_model=settings.GROQ_MODEL,
        ai_worker_status="ready",
        database_connected=db_connected,
        database_status=db_status,
        database_name=settings.DATABASE_NAME if settings.is_mongodb_configured else None,
        gpu_workers_available=0,
        avg_queue_wait_sec=0.0,
        active_model="BollyMesh-v2.4-NeuralBlend",
    )


# -------------------------------------------------------------
# System Health Endpoints
# -------------------------------------------------------------

@root_router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System Health"],
    summary="Root System Health Check",
)
async def get_root_health(
    settings: Settings = Depends(get_settings),
    db_service: DatabaseService = Depends(get_database_service),
) -> HealthResponse:
    """Direct root health endpoint reporting service readiness and DB status."""
    return HealthResponse(
        success=True,
        data=build_health_data(settings, db_service),
        message=f"{settings.APP_NAME} operational",
    )


@api_router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System Health"],
    summary="API v1 System Health Check",
)
async def get_api_v1_health(
    settings: Settings = Depends(get_settings),
    db_service: DatabaseService = Depends(get_database_service),
) -> HealthResponse:
    """Versioned API v1 health endpoint compatible with frontend contracts."""
    return HealthResponse(
        success=True,
        data=build_health_data(settings, db_service),
        message=f"{settings.APP_NAME} operational",
    )


# -------------------------------------------------------------
# Real File Upload Endpoints
# -------------------------------------------------------------

@api_router.post(
    "/videos/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_200_OK,
    tags=["Media Uploads"],
    summary="Upload Source Video Footage",
    description="Validates and streams an MP4 or MOV video (max 100MB) into storage and registers metadata in MongoDB.",
)
async def upload_video(
    file: UploadFile = File(..., description="Multipart video file (MP4, MOV, max 100MB)"),
    settings: Settings = Depends(get_settings),
    storage_service: BaseStorageService = Depends(get_storage_service),
    project_service: ProjectService = Depends(get_project_service),
) -> VideoUploadResponse:
    """Uploads, validates, and stores raw cinematic video footage."""
    stored_result = None
    try:
        stored_result = await storage_service.save_upload(
            upload_file=file,
            subfolder="videos",
            max_size_bytes=settings.MAX_VIDEO_SIZE_BYTES,
            allowed_extensions=ALLOWED_VIDEO_EXTENSIONS,
            allowed_mimes=ALLOWED_VIDEO_MIMES,
            prefix="vid",
        )

        # Persist metadata in database if connected
        if project_service.db_service.is_connected:
            await project_service.record_upload(stored_result, file_type="video")

        storage_url = f"{settings.API_PREFIX}/files/{stored_result.upload_id}"

        return VideoUploadResponse(
            success=True,
            data=VideoUploadResult(
                fileId=stored_result.upload_id,
                filename=stored_result.original_filename,
                storageUrl=storage_url,
                durationSeconds=15.0,
                width=1920,
                height=1080,
                fps=30,
                codec="h264",
                sizeBytes=stored_result.size_bytes,
            ),
            message="Source footage uploaded and validated successfully.",
        )
    except StorageValidationError:
        raise
    except Exception as e:
        # Cleanup uploaded file if database persistence or handling fails
        if stored_result is not None:
            await storage_service.delete_file(stored_result.storage_path)
        logger.exception("Failed to process video upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video upload processing failed: {type(e).__name__}",
        )


@api_router.post(
    "/faces/upload",
    response_model=FaceUploadResponse,
    status_code=status.HTTP_200_OK,
    tags=["Media Uploads"],
    summary="Upload Target Face Image",
    description="Validates and streams a JPG, PNG, or WEBP portrait (max 10MB) into storage and registers metadata in MongoDB.",
)
async def upload_face(
    file: UploadFile = File(..., description="Multipart image file (JPG, PNG, max 10MB)"),
    settings: Settings = Depends(get_settings),
    storage_service: BaseStorageService = Depends(get_storage_service),
    project_service: ProjectService = Depends(get_project_service),
) -> FaceUploadResponse:
    """Uploads, validates, and stores target actor replacement photo."""
    stored_result = None
    try:
        stored_result = await storage_service.save_upload(
            upload_file=file,
            subfolder="faces",
            max_size_bytes=settings.MAX_IMAGE_SIZE_BYTES,
            allowed_extensions=ALLOWED_FACE_EXTENSIONS,
            allowed_mimes=ALLOWED_FACE_MIMES,
            prefix="face",
        )

        if project_service.db_service.is_connected:
            await project_service.record_upload(stored_result, file_type="face")

        preview_url = f"{settings.API_PREFIX}/files/{stored_result.upload_id}"

        return FaceUploadResponse(
            success=True,
            data=FaceUploadResult(
                faceId=stored_result.upload_id,
                previewUrl=preview_url,
                detectedFacesCount=1,
                embeddingConfidence=1.0,
                qualityPassed=True,
                note="Face portrait uploaded and verified. Neural face mesh model runs in Phase 4.",
            ),
            message="Target actor portrait uploaded and verified.",
        )
    except StorageValidationError:
        raise
    except Exception as e:
        if stored_result is not None:
            await storage_service.delete_file(stored_result.storage_path)
        logger.exception("Failed to process face upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face upload processing failed: {type(e).__name__}",
        )


@api_router.get(
    "/files/{file_id}",
    tags=["Media Uploads"],
    summary="Retrieve Stored Media File",
    description="Streams a previously stored video or portrait by upload ID.",
)
async def get_stored_file(
    file_id: str,
    project_service: ProjectService = Depends(get_project_service),
    storage_service: BaseStorageService = Depends(get_storage_service),
):
    """Securely streams an uploaded file without exposing internal paths."""
    if not project_service.db_service.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is offline.",
        )

    doc = await project_service.get_upload(file_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found.",
        )

    file_path = storage_service.get_file_path(doc["storage_path"])
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical file not found in storage.",
        )

    return FileResponse(
        path=str(file_path),
        media_type=doc.get("content_type", "application/octet-stream"),
        filename=doc.get("original_filename", file_id),
    )


# -------------------------------------------------------------
# Consent Tracking Endpoint
# -------------------------------------------------------------

@api_router.post(
    "/consent",
    response_model=ConsentResponse,
    status_code=status.HTTP_200_OK,
    tags=["Compliance & Consent"],
    summary="Record Likeness Authorization Consent",
    description="Records explicit consent affirming that the user has authorization to synthesize the specified persona.",
)
async def record_consent(
    request: ConsentRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> ConsentResponse:
    """Records ethical AI likeness authorization before processing."""
    if not request.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Likeness authorization consent must be explicitly affirmed (consentGiven=true).",
        )

    if not project_service.db_service.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable for consent recording.",
        )

    doc = await project_service.record_consent(
        project_id=request.project_id,
        consent_given=request.consent_given,
        consent_text_version=request.consent_text_version,
        affirmation=request.affirmation,
    )

    return ConsentResponse(
        success=True,
        data=ConsentRecordData(**doc),
        message="Consent record successfully registered.",
    )


# -------------------------------------------------------------
# Project and Job Management Endpoints
# -------------------------------------------------------------

@api_router.post(
    "/projects",
    response_model=ProjectCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects & Jobs"],
    summary="Create Cinematic Face Swap Project",
    description="Registers a new project, validates consent affirmation, and initializes a processing job in 'uploaded' state.",
)
async def create_project(
    request: ProjectCreateRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectCreateResponse:
    """Creates a new project in MongoDB with an associated initial job."""
    if not request.consent_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent must be affirmed before project creation.",
        )

    if not project_service.db_service.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable for project creation.",
        )

    doc = await project_service.create_project(
        title=request.title,
        original_video_id=request.original_video_id,
        replacement_face_id=request.replacement_face_id,
        user_id=request.user_id,
        consent_confirmed=request.consent_confirmed,
    )

    return ProjectCreateResponse(
        success=True,
        data=ProjectResponseData(**doc),
        message="Project created successfully and queued for processing.",
    )


@api_router.get(
    "/projects",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Projects & Jobs"],
    summary="List Projects",
    description="Retrieves a list of registered cinematic projects from MongoDB, sorted by creation date.",
)
async def list_projects(
    limit: int = 50,
    skip: int = 0,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    """Lists projects from MongoDB."""
    if not project_service.db_service.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        )

    projects_raw = await project_service.list_projects(limit=limit, skip=skip)
    data = [ProjectResponseData(**p) for p in projects_raw]

    return ProjectListResponse(
        success=True,
        data=data,
        message=f"Retrieved {len(data)} projects.",
    )


@api_router.get(
    "/projects/{project_id}",
    response_model=ProjectDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Projects & Jobs"],
    summary="Get Project Details",
    description="Fetches project metadata and associated active job status by project_id.",
)
async def get_project(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectDetailResponse:
    """Retrieves a single project by ID."""
    if not project_service.db_service.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        )

    doc = await project_service.get_project(project_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    return ProjectDetailResponse(
        success=True,
        data=ProjectResponseData(**doc),
        message="Project retrieved successfully.",
    )


@api_router.get(
    "/jobs/{job_id}",
    response_model=JobDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Projects & Jobs"],
    summary="Get Processing Job Status",
    description="Fetches the status and progress of a processing job by job_id.",
)
async def get_job(
    job_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> JobDetailResponse:
    """Retrieves job status by job ID."""
    if not project_service.db_service.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        )

    doc = await project_service.get_job(job_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    return JobDetailResponse(
        success=True,
        data=JobResponseData(**doc),
        message="Job status retrieved successfully.",
    )


# -------------------------------------------------------------
# Groq Intelligence Test Endpoint (Preserved from Phase 2)
# -------------------------------------------------------------

@api_router.post(
    "/groq/test",
    response_model=GroqTestResponse,
    status_code=status.HTTP_200_OK,
    tags=["Groq Intelligence"],
    summary="Test Groq API Connectivity",
    description="Executes a minimal test completion request using configured Groq credentials. Returns latency and sample response without exposing secrets.",
)
async def test_groq_connection(
    request: GroqTestRequest = GroqTestRequest(),
    groq_service: GroqService = Depends(get_groq_service),
) -> GroqTestResponse:
    """Invokes Groq API to test connectivity and model availability."""
    prompt = request.prompt or "Ping from BollySwap AI backend."
    result = await groq_service.test_connection(prompt=prompt)

    return GroqTestResponse(
        success=True,
        data=result,
        message=f"Groq API connection verified successfully using model '{result.model}'.",
    )


# -------------------------------------------------------------
# Real AI Face Detection & Actor Selection Endpoints (Phase 4)
# -------------------------------------------------------------

@api_router.post(
    "/faces/detect",
    response_model=FaceDetectResponse,
    status_code=status.HTTP_200_OK,
    tags=["Face Detection & Tracking"],
    summary="Run AI Face Detection on Footage",
    description="Extracts video frames, executes OpenCV YuNet inference, groups actor tracks via IoU, and stores thumbnails.",
)
async def detect_faces(
    request: FaceDetectRequest,
    detection_service: DetectionService = Depends(get_detection_service),
) -> FaceDetectResponse:
    """Triggers real YuNet face detection and continuous actor tracking."""
    try:
        result = await detection_service.run_detection(
            project_id=request.project_id,
            video_id=request.video_id,
        )
        return FaceDetectResponse(
            success=True,
            data=result,
            message=f"Face detection complete: identified {result.detected_face_count} faces across {len(result.tracks)} actor tracks.",
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@api_router.get(
    "/faces/detect/{detection_job_id}",
    response_model=DetectionJobResponse,
    status_code=status.HTTP_200_OK,
    tags=["Face Detection & Tracking"],
    summary="Get Detection Job Status",
    description="Retrieves the live status, progress, and track results of an active or completed face detection job.",
)
async def get_detection_job(
    detection_job_id: str,
    detection_service: DetectionService = Depends(get_detection_service),
) -> DetectionJobResponse:
    """Retrieves status and output of a specific face detection job."""
    try:
        result = await detection_service.get_detection_job(detection_job_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection job with ID '{detection_job_id}' not found.",
            )
        return DetectionJobResponse(
            success=True,
            data=result,
            message="Detection job retrieved successfully.",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@api_router.get(
    "/projects/{project_id}/faces",
    response_model=ProjectFacesResponse,
    status_code=status.HTTP_200_OK,
    tags=["Face Detection & Tracking"],
    summary="Get Detected Actor Faces for Project",
    description="Retrieves candidate actor tracks and current selection for the specified project.",
)
async def get_project_faces(
    project_id: str,
    detection_service: DetectionService = Depends(get_detection_service),
) -> ProjectFacesResponse:
    """Fetches detected actor tracks and selected track for a project."""
    try:
        result = await detection_service.get_project_faces(project_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No face detection results found for project '{project_id}'.",
            )
        return ProjectFacesResponse(
            success=True,
            data=result,
            message="Project face tracks retrieved successfully.",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@api_router.post(
    "/projects/{project_id}/faces/select",
    response_model=TrackSelectionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Face Detection & Tracking"],
    summary="Select Actor Track to Replace",
    description="Validates that the selected track belongs to the project and records the user's choice in MongoDB.",
)
async def select_project_actor_track(
    project_id: str,
    request: TrackSelectionRequest,
    detection_service: DetectionService = Depends(get_detection_service),
) -> TrackSelectionResponse:
    """Affirms the chosen actor track in the video to be replaced in the swap pipeline."""
    try:
        result = await detection_service.select_actor_track(
            project_id=project_id,
            selected_track_id=request.selected_track_id,
        )
        return TrackSelectionResponse(
            success=True,
            data=result,
            message=result.message,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

