import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.services.database import DatabaseService, get_database_service
from app.services.storage_service import FileStorageResult

logger = logging.getLogger("bollyswap.services.project")


def current_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectService:
    """
    Handles MongoDB persistence for Projects, Processing Jobs, Consent Records, and Uploads.
    """

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    async def record_upload(
        self,
        storage_result: FileStorageResult,
        file_type: str,
    ) -> Dict[str, Any]:
        """Saves file upload metadata in the 'uploads' collection."""
        if not self.db_service.is_connected:
            raise RuntimeError("Database connection is not available for recording uploads.")

        collection = self.db_service.get_collection("uploads")
        now = current_iso_timestamp()

        doc = {
            "upload_id": storage_result.upload_id,
            "file_type": file_type,
            "filename": storage_result.filename,
            "original_filename": storage_result.original_filename,
            "content_type": storage_result.content_type,
            "size_bytes": storage_result.size_bytes,
            "storage_path": storage_result.storage_path,
            "created_at": now,
        }

        await collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def get_upload(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves upload metadata by upload_id."""
        if not self.db_service.is_connected:
            raise RuntimeError("Database connection is not available.")

        collection = self.db_service.get_collection("uploads")
        doc = await collection.find_one({"upload_id": upload_id})
        if doc:
            doc.pop("_id", None)
        return doc

    async def record_consent(
        self,
        project_id: str,
        consent_given: bool,
        consent_text_version: str = "v1.0",
        affirmation: str = "Authorized likeness and creative usage affirmed.",
    ) -> Dict[str, Any]:
        """Records explicit consent before project submission."""
        if not self.db_service.is_connected:
            raise RuntimeError("Database connection is not available for recording consent.")

        if not consent_given:
            raise ValueError("Consent must be explicitly affirmed.")

        collection = self.db_service.get_collection("consent_records")
        consent_id = f"cst_{uuid.uuid4().hex[:12]}"
        now = current_iso_timestamp()

        doc = {
            "consent_id": consent_id,
            "project_id": project_id,
            "consent_given": consent_given,
            "consent_text_version": consent_text_version,
            "affirmation": affirmation,
            "created_at": now,
        }

        await collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def has_consent(self, project_id: str) -> bool:
        """Checks if a valid consent record exists for the project."""
        if not self.db_service.is_connected:
            return False
        collection = self.db_service.get_collection("consent_records")
        doc = await collection.find_one({"project_id": project_id, "consent_given": True})
        return doc is not None

    async def create_project(
        self,
        title: str,
        original_video_id: str,
        replacement_face_id: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        consent_confirmed: bool = True,
        initial_job_status: str = "uploaded",
    ) -> Dict[str, Any]:
        """
        Creates a new project record and initiates an honest processing job record.
        """
        if not self.db_service.is_connected:
            raise RuntimeError("Database connection is not available for creating projects.")

        if not consent_confirmed:
            raise ValueError("Likeness authorization consent is strictly required.")

        proj_id = project_id or f"proj_{uuid.uuid4().hex[:12]}"
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = current_iso_timestamp()

        # 1. Insert Project
        projects_col = self.db_service.get_collection("projects")
        project_doc = {
            "project_id": proj_id,
            "user_id": user_id,
            "title": title.strip() or "Untitled Cinematic Project",
            "original_video_id": original_video_id,
            "replacement_face_id": replacement_face_id,
            "status": initial_job_status,
            "created_at": now,
            "updated_at": now,
        }
        await projects_col.insert_one(project_doc)
        project_doc.pop("_id", None)

        # 2. Insert Processing Job
        jobs_col = self.db_service.get_collection("processing_jobs")
        job_doc = {
            "job_id": job_id,
            "project_id": proj_id,
            "status": initial_job_status,
            "progress": 0.0,
            "current_stage": "Asset Ingestion Complete — Awaiting Phase 4 Processing Pipeline",
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        await jobs_col.insert_one(job_doc)
        job_doc.pop("_id", None)

        # 3. Record consent if not already recorded
        try:
            await self.record_consent(
                project_id=proj_id,
                consent_given=True,
                consent_text_version="v1.0",
                affirmation="Consent affirmed during project creation.",
            )
        except Exception as e:
            logger.warning("Consent record duplicate or non-fatal: %s", e)

        project_doc["active_job"] = job_doc
        return project_doc

    async def list_projects(self, limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """Lists projects sorted by created_at descending."""
        if not self.db_service.is_connected:
            raise RuntimeError("Database connection is not available.")

        projects_col = self.db_service.get_collection("projects")
        cursor = projects_col.find({}).sort("created_at", -1).skip(skip).limit(limit)

        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(doc)

        return results

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves project details by project_id including latest job."""
        if not self.db_service.is_connected:
            raise RuntimeError("Database connection is not available.")

        projects_col = self.db_service.get_collection("projects")
        doc = await projects_col.find_one({"project_id": project_id})
        if not doc:
            return None

        doc.pop("_id", None)

        # Attach latest job
        jobs_col = self.db_service.get_collection("processing_jobs")
        job_doc = await jobs_col.find_one({"project_id": project_id}, sort=[("created_at", -1)])
        if job_doc:
            job_doc.pop("_id", None)
            doc["active_job"] = job_doc

        return doc

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a processing job by job_id."""
        if not self.db_service.is_connected:
            raise RuntimeError("Database connection is not available.")

        jobs_col = self.db_service.get_collection("processing_jobs")
        doc = await jobs_col.find_one({"job_id": job_id})
        if doc:
            doc.pop("_id", None)
        return doc


def get_project_service() -> ProjectService:
    """FastAPI dependency for ProjectService."""
    return ProjectService(db_service=get_database_service())

