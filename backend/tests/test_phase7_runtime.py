import pytest
from unittest.mock import MagicMock
from pathlib import Path
import numpy as np

from app.services.face_detector import get_shared_yunet_detector, reset_shared_yunet_detector
from app.services.video_processing.model_adapter import (
    get_face_swap_model_adapter,
    reset_face_swap_model_adapter,
    LicensedFaceSwapModelAdapter,
)
from app.services.detection_service import (
    DetectionService,
    get_detection_service,
    reset_detection_service,
)
from app.services.video_processing.processing_pipeline import (
    VideoProcessingPipeline,
    get_video_processing_pipeline,
    reset_video_processing_pipeline,
)
from app.services.project_service import ProjectService
from app.core.config import get_settings


class InMemoryAsyncCollection:
    """Deterministic mock MongoDB collection supporting queries and upserts."""
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        stored = dict(doc)
        stored["_id"] = f"mock_{len(self.docs)}"
        self.docs.append(stored)
        res = MagicMock()
        res.inserted_id = stored["_id"]
        return res

    async def update_one(self, query, update, upsert=False):
        for doc in self.docs:
            match = all(doc.get(k) == v for k, v in query.items())
            if match:
                if "$set" in update:
                    doc.update(update["$set"])
                res = MagicMock()
                res.modified_count = 1
                return res
        if upsert:
            new_doc = dict(query)
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            if "$set" in update:
                new_doc.update(update["$set"])
            new_doc["_id"] = f"mock_{len(self.docs)}"
            self.docs.append(new_doc)
            res = MagicMock()
            res.upserted_id = new_doc["_id"]
            return res
        res = MagicMock()
        res.modified_count = 0
        return res

    async def find_one(self, query, sort=None):
        docs_to_search = list(reversed(self.docs)) if sort else self.docs
        for doc in docs_to_search:
            match = all(doc.get(k) == v for k, v in query.items())
            if match:
                return dict(doc)
        return None


class MockDatabaseService:
    def __init__(self):
        self.is_connected = True
        self.collections = {
            "projects": InMemoryAsyncCollection(),
            "detection_jobs": InMemoryAsyncCollection(),
            "consent_records": InMemoryAsyncCollection(),
            "uploads": InMemoryAsyncCollection(),
            "processing_jobs": InMemoryAsyncCollection(),
            "swap_jobs": InMemoryAsyncCollection(),
        }

    def get_collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = InMemoryAsyncCollection()
        return self.collections[name]


@pytest.mark.anyio
async def test_face_selection_on_auto_upserted_project():
    """
    Verifies that selecting an actor track succeeds even if the project document
    was not pre-created before face detection, resolving the runtime 400 Bad Request error.
    """
    db = MockDatabaseService()
    settings = get_settings()
    detection_svc = DetectionService(
        settings=settings,
        db_service=db,
        storage_service=MagicMock(),
    )

    project_id = "proj_client_generated_123"
    detection_job_id = "det_job_456"

    # Seed detection job with 2 candidate tracks
    jobs_col = db.get_collection("detection_jobs")
    await jobs_col.insert_one({
        "detection_job_id": detection_job_id,
        "project_id": project_id,
        "video_id": "vid_test_1",
        "detection_status": "completed",
        "tracks": [
            {
                "track_id": "track_1",
                "label": "Actor #1",
                "confidence": 0.95,
                "thumbnail_file_id": "thumb_file_1",
                "thumbnail_url": "/api/v1/files/thumb_file_1",
                "occurrences": 12,
                "timestamps": [0.0, 1.5, 3.0],
                "bounding_box": {"x": 100, "y": 100, "width": 80, "height": 80},
                "landmarks": [[110, 110], [130, 110], [120, 125], [115, 140], [125, 140]],
            },
            {
                "track_id": "track_2",
                "label": "Actor #2",
                "confidence": 0.88,
                "thumbnail_file_id": "thumb_file_2",
                "thumbnail_url": "/api/v1/files/thumb_file_2",
                "occurrences": 8,
                "timestamps": [1.5, 3.0],
                "bounding_box": {"x": 300, "y": 150, "width": 75, "height": 75},
                "landmarks": [[310, 160], [330, 160], [320, 175], [315, 190], [325, 190]],
            },
        ],
        "created_at": "2026-11-02T12:00:00Z",
    })

    # Select actor track_2 without pre-existing project doc
    result = await detection_svc.select_actor_track(
        project_id=project_id,
        selected_track_id="track_2",
    )

    assert result.project_id == project_id
    assert result.selected_track_id == "track_2"
    assert result.selected_track is not None
    assert result.selected_track.label == "Actor #2"

    # Verify project document was created and track persisted
    projects_col = db.get_collection("projects")
    proj_doc = await projects_col.find_one({"project_id": project_id})
    assert proj_doc is not None
    assert proj_doc["selected_actor_track_id"] == "track_2"


@pytest.mark.anyio
async def test_face_selection_rejects_thumbnail_file_id():
    """
    Verifies that if a client mistakenly submits a thumbnail file ID instead of
    a track ID, the backend returns a clear, actionable validation error.
    """
    db = MockDatabaseService()
    settings = get_settings()
    detection_svc = DetectionService(
        settings=settings,
        db_service=db,
        storage_service=MagicMock(),
    )

    project_id = "proj_test_thumb"
    jobs_col = db.get_collection("detection_jobs")
    await jobs_col.insert_one({
        "detection_job_id": "det_job_thumb",
        "project_id": project_id,
        "video_id": "vid_test_1",
        "tracks": [
            {
                "track_id": "track_1",
                "label": "Actor #1",
                "confidence": 0.95,
                "thumbnail_file_id": "thumb_file_abc",
                "thumbnail_url": "/api/v1/files/thumb_file_abc",
                "occurrences": 10,
                "timestamps": [0.0],
                "bounding_box": {"x": 10, "y": 10, "width": 50, "height": 50},
            }
        ],
        "created_at": "2026-11-02T12:00:00Z",
    })

    with pytest.raises(ValueError) as excinfo:
        await detection_svc.select_actor_track(
            project_id=project_id,
            selected_track_id="thumb_file_abc",
        )

    assert "thumbnail file ID, not a valid actor track ID" in str(excinfo.value)
    assert "track_1" in str(excinfo.value)


@pytest.mark.anyio
async def test_face_selection_rejects_nonexistent_track_id():
    """
    Verifies that non-existent track IDs are rejected with a clear message
    listing available tracks.
    """
    db = MockDatabaseService()
    settings = get_settings()
    detection_svc = DetectionService(
        settings=settings,
        db_service=db,
        storage_service=MagicMock(),
    )

    project_id = "proj_test_nonexistent"
    jobs_col = db.get_collection("detection_jobs")
    await jobs_col.insert_one({
        "detection_job_id": "det_job_none",
        "project_id": project_id,
        "video_id": "vid_test_1",
        "tracks": [
            {
                "track_id": "track_1",
                "label": "Actor #1",
                "confidence": 0.95,
                "thumbnail_file_id": "thumb_file_1",
                "thumbnail_url": "/api/v1/files/thumb_file_1",
                "occurrences": 10,
                "timestamps": [0.0],
                "bounding_box": {"x": 10, "y": 10, "width": 50, "height": 50},
            }
        ],
        "created_at": "2026-11-02T12:00:00Z",
    })

    with pytest.raises(ValueError) as excinfo:
        await detection_svc.select_actor_track(
            project_id=project_id,
            selected_track_id="track_99",
        )

    assert "does not belong to project" in str(excinfo.value)
    assert "track_1" in str(excinfo.value)


@pytest.mark.anyio
async def test_project_create_preserves_existing_tracks():
    """
    Verifies that when create_project is called for a project ID that already
    has detected tracks from face detection, the tracks and selection are preserved.
    """
    db = MockDatabaseService()
    proj_svc = ProjectService(db_service=db)

    project_id = "proj_preserve_tracks"
    projects_col = db.get_collection("projects")
    await projects_col.insert_one({
        "project_id": project_id,
        "title": "Initial Title",
        "original_video_id": "vid_orig",
        "replacement_face_id": "",
        "detected_tracks": [{"track_id": "track_1", "label": "Lead Hero"}],
        "selected_actor_track_id": "track_1",
        "status": "awaiting_face_selection",
        "created_at": "2026-11-02T12:00:00Z",
        "updated_at": "2026-11-02T12:00:00Z",
    })

    # Call create_project with the same project_id
    updated = await proj_svc.create_project(
        project_id=project_id,
        title="Updated Cinematic Title",
        original_video_id="vid_orig_confirmed",
        replacement_face_id="face_confirmed_1",
        consent_confirmed=True,
    )

    assert updated["project_id"] == project_id
    assert updated["title"] == "Updated Cinematic Title"
    assert updated["original_video_id"] == "vid_orig_confirmed"
    assert updated["replacement_face_id"] == "face_confirmed_1"
    # Preserved tracks and selection:
    assert updated["selected_actor_track_id"] == "track_1"
    assert len(updated["detected_tracks"]) == 1
    assert updated["detected_tracks"][0]["label"] == "Lead Hero"


def test_face_swap_model_adapter_singleton():
    """
    Verifies that get_face_swap_model_adapter() returns the exact same instance
    on repeated calls, preventing expensive repeated ONNX model initialization.
    """
    reset_face_swap_model_adapter()
    adapter1 = get_face_swap_model_adapter()
    adapter2 = get_face_swap_model_adapter()

    assert adapter1 is adapter2, "Model adapter must be a shared singleton"
    assert adapter1.is_available, "Licensed face swap model adapter should be ready"


def test_shared_yunet_detector_singleton():
    """
    Verifies that get_shared_yunet_detector() returns the exact same FaceDetectorYuNet
    instance across repeated invocations.
    """
    reset_shared_yunet_detector()
    detector1 = get_shared_yunet_detector()
    detector2 = get_shared_yunet_detector()

    assert detector1 is detector2, "FaceDetectorYuNet must be a shared singleton"
    assert detector1.model_path.exists(), "YuNet model file must exist on disk"


def test_services_singletons():
    """
    Verifies that get_detection_service and get_video_processing_pipeline return
    cached singletons to avoid repeated resource allocations.
    """
    reset_detection_service()
    reset_video_processing_pipeline()

    det1 = get_detection_service()
    det2 = get_detection_service()
    assert det1 is det2, "DetectionService must be a shared singleton"

    pipe1 = get_video_processing_pipeline()
    pipe2 = get_video_processing_pipeline()
    assert pipe1 is pipe2, "VideoProcessingPipeline must be a shared singleton"
