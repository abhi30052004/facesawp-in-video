import abc
import os
import re
import uuid
import logging
from pathlib import Path
from typing import Optional, Set, Tuple
from fastapi import UploadFile

logger = logging.getLogger("bollyswap.services.storage")

# Magic signatures
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
WEBP_RIFF = b"RIFF"
WEBP_TAG = b"WEBP"
WEBM_MAGIC = b"\x1aE\xdf\xa3"


class StorageValidationError(Exception):
    """Raised when an uploaded file violates format, size, or signature constraints."""
    def __init__(self, message: str, error_code: str = "INVALID_FILE"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class FileStorageResult:
    """Encapsulates safe metadata for a successfully stored file."""
    def __init__(
        self,
        upload_id: str,
        storage_path: str,
        filename: str,
        original_filename: str,
        content_type: str,
        size_bytes: int,
    ):
        self.upload_id = upload_id
        self.storage_path = storage_path
        self.filename = filename
        self.original_filename = original_filename
        self.content_type = content_type
        self.size_bytes = size_bytes


class BaseStorageService(abc.ABC):
    """
    Abstract storage provider interface.
    Allows seamlessly swapping LocalStorageService with Cloudflare R2 / S3 in production.
    """

    @abc.abstractmethod
    async def save_upload(
        self,
        upload_file: UploadFile,
        subfolder: str,
        max_size_bytes: int,
        allowed_extensions: Set[str],
        allowed_mimes: Set[str],
        prefix: str = "file",
    ) -> FileStorageResult:
        """Streams and validates an uploaded file to storage."""
        pass

    @abc.abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """Deletes a file by relative storage path."""
        pass

    @abc.abstractmethod
    def get_file_path(self, storage_path: str) -> Path:
        """Returns the filesystem path for local access."""
        pass

    @abc.abstractmethod
    async def save_bytes(
        self,
        data: bytes,
        subfolder: str,
        extension: str,
        prefix: str = "file",
        content_type: str = "image/jpeg",
        original_filename: str = "file.jpg",
    ) -> FileStorageResult:
        """Saves a binary buffer directly to storage."""
        pass


class LocalStorageService(BaseStorageService):
    """
    Local filesystem implementation of the storage provider.
    Enforces chunked streaming, magic byte validation, and path traversal prevention.
    """

    CHUNK_SIZE = 1024 * 1024  # 1 MB chunk

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Creates storage subdirectories if they do not exist."""
        for folder in ["videos", "faces", "temp"]:
            target = self.base_dir / folder
            target.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_filename(filename: Optional[str]) -> str:
        """Sanitizes user filename, stripping dangerous characters and paths."""
        if not filename:
            return "unnamed"
        # Extract base name to defeat path traversal attacks
        base = os.path.basename(filename)
        cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)
        return cleaned[:80] if cleaned else "unnamed"

    @staticmethod
    def validate_file_signature(header: bytes, ext: str, content_type: str) -> bool:
        """
        Validates the actual binary magic bytes against expected file format.
        Prevents extension-spoofing attacks (e.g. uploading a script disguised as an MP4).
        """
        ext_lower = ext.lower().lstrip(".")

        # Image Signatures
        if ext_lower == "png":
            return header.startswith(PNG_MAGIC)
        if ext_lower in ("jpg", "jpeg"):
            return header.startswith(JPEG_MAGIC)
        if ext_lower == "webp":
            return len(header) >= 12 and header.startswith(WEBP_RIFF) and header[8:12] == WEBP_TAG

        # Video Signatures
        if ext_lower in ("mp4", "mov"):
            # ISO Base Media File Format: 'ftyp' typically at offset 4..8
            # or QuickTime 'moov' / 'mdat' / 'wide' atom
            if len(header) >= 8:
                box_type = header[4:8]
                if box_type in (b"ftyp", b"moov", b"mdat", b"wide", b"skip"):
                    return True
                # Quick check if ftyp is within first 16 bytes
                if b"ftyp" in header[:16]:
                    return True
            return False

        if ext_lower == "webm":
            return header.startswith(WEBM_MAGIC)

        return False

    async def save_upload(
        self,
        upload_file: UploadFile,
        subfolder: str,
        max_size_bytes: int,
        allowed_extensions: Set[str],
        allowed_mimes: Set[str],
        prefix: str = "file",
    ) -> FileStorageResult:
        """
        Validates, streams, and saves an upload file safely in chunks.
        """
        original_name = self.sanitize_filename(upload_file.filename)
        ext = Path(original_name).suffix.lower()

        # 1. Extension check
        if ext not in allowed_extensions:
            allowed_list = ", ".join(sorted(allowed_extensions))
            raise StorageValidationError(
                f"Unsupported file extension '{ext}'. Allowed extensions: {allowed_list}.",
                error_code="INVALID_EXTENSION",
            )

        # 2. Content-Type check (liberal to handle diverse browsers, but checked)
        declared_mime = (upload_file.content_type or "").lower().strip()
        if declared_mime and declared_mime not in allowed_mimes and "octet-stream" not in declared_mime:
            allowed_list = ", ".join(sorted(allowed_mimes))
            raise StorageValidationError(
                f"Unsupported content type '{declared_mime}'. Expected: {allowed_list}.",
                error_code="INVALID_MIME_TYPE",
            )

        # Generate unique server filename and secure path
        upload_id = f"{prefix}_{uuid.uuid4().hex[:16]}"
        safe_server_filename = f"{upload_id}{ext}"
        destination_folder = (self.base_dir / subfolder).resolve()

        # Path traversal guard
        if not str(destination_folder).startswith(str(self.base_dir)):
            raise StorageValidationError("Invalid destination storage folder.", error_code="SECURITY_ERROR")

        destination_folder.mkdir(parents=True, exist_ok=True)
        target_path = destination_folder / safe_server_filename

        total_bytes = 0
        header_bytes = bytearray()
        signature_checked = False

        try:
            with open(target_path, "wb") as out_file:
                while True:
                    chunk = await upload_file.read(self.CHUNK_SIZE)
                    if not chunk:
                        break

                    total_bytes += len(chunk)

                    # Size validation guard
                    if total_bytes > max_size_bytes:
                        limit_mb = round(max_size_bytes / (1024 * 1024), 1)
                        raise StorageValidationError(
                            f"File size exceeds maximum allowable limit of {limit_mb} MB.",
                            error_code="FILE_TOO_LARGE",
                        )

                    # Accumulate header for signature validation
                    if not signature_checked:
                        header_bytes.extend(chunk)
                        if len(header_bytes) >= 64:
                            if not self.validate_file_signature(bytes(header_bytes), ext, declared_mime):
                                raise StorageValidationError(
                                    f"File signature validation failed. The contents of '{original_name}' do not match a valid {ext.upper()} format.",
                                    error_code="INVALID_FILE_SIGNATURE",
                                )
                            signature_checked = True

                    out_file.write(chunk)

            # Check signature if file was smaller than 64 bytes
            if not signature_checked:
                if len(header_bytes) < 8 or not self.validate_file_signature(bytes(header_bytes), ext, declared_mime):
                    raise StorageValidationError(
                        f"File signature validation failed for '{original_name}'.",
                        error_code="INVALID_FILE_SIGNATURE",
                    )

            if total_bytes == 0:
                raise StorageValidationError("Uploaded file is empty (0 bytes).", error_code="EMPTY_FILE")

            relative_storage_path = f"{subfolder}/{safe_server_filename}"

            logger.info("Stored %s bytes at %s (id: %s)", total_bytes, relative_storage_path, upload_id)

            return FileStorageResult(
                upload_id=upload_id,
                storage_path=relative_storage_path,
                filename=safe_server_filename,
                original_filename=original_name,
                content_type=declared_mime or "application/octet-stream",
                size_bytes=total_bytes,
            )

        except Exception:
            # Clean up partial/orphaned file upon validation or I/O failure
            if target_path.exists():
                try:
                    target_path.unlink()
                except Exception as del_err:
                    logger.warning("Failed to clean up partial file %s: %s", target_path, del_err)
            raise

    async def delete_file(self, storage_path: str) -> bool:
        """Deletes a file by relative storage path."""
        try:
            target = (self.base_dir / storage_path).resolve()
            # Prevent path traversal
            if not str(target).startswith(str(self.base_dir)):
                return False
            if target.exists() and target.is_file():
                target.unlink()
                logger.info("Deleted stored file: %s", storage_path)
                return True
            return False
        except Exception as e:
            logger.warning("Error deleting file %s: %s", storage_path, e)
            return False

    def get_file_path(self, storage_path: str) -> Path:
        """Resolves the local Path, strictly preventing path traversal."""
        target = (self.base_dir / storage_path).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise ValueError("Path traversal attempt detected.")
        return target

    async def save_bytes(
        self,
        data: bytes,
        subfolder: str,
        extension: str,
        prefix: str = "file",
        content_type: str = "image/jpeg",
        original_filename: str = "file.jpg",
    ) -> FileStorageResult:
        """Saves a binary buffer directly to storage safely."""
        upload_id = f"{prefix}_{uuid.uuid4().hex[:16]}"
        ext = f".{extension.lstrip('.')}"
        safe_server_filename = f"{upload_id}{ext}"
        destination_folder = (self.base_dir / subfolder).resolve()

        if not str(destination_folder).startswith(str(self.base_dir)):
            raise StorageValidationError("Invalid destination folder.", error_code="SECURITY_ERROR")

        destination_folder.mkdir(parents=True, exist_ok=True)
        target_path = destination_folder / safe_server_filename

        with open(target_path, "wb") as f:
            f.write(data)

        relative_storage_path = f"{subfolder}/{safe_server_filename}"
        logger.info("Saved %s bytes directly at %s (id: %s)", len(data), relative_storage_path, upload_id)

        return FileStorageResult(
            upload_id=upload_id,
            storage_path=relative_storage_path,
            filename=safe_server_filename,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=len(data),
        )


def get_storage_service() -> BaseStorageService:
    """Dependency provider for storage service."""
    from app.core.config import get_settings
    settings = get_settings()
    return LocalStorageService(base_dir=settings.resolved_storage_dir)
