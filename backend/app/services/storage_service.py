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
    def get_download_url(self, storage_path: str) -> Optional[str]:
        """Returns public or presigned download URL if remote, or None if local."""
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

    def get_download_url(self, storage_path: str) -> Optional[str]:
        """Local storage serves files directly from local disk, so no remote URL."""
        return None

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


class S3R2StorageService(BaseStorageService):
    """
    Cloudflare R2 / AWS S3 compatible persistent object storage implementation.
    Safely validates file signatures, streams to S3/R2, and maintains a local cache
    for OpenCV/FFmpeg filesystem access on ephemeral container environments (e.g. Render).
    """

    CHUNK_SIZE = 1024 * 1024  # 1 MB chunk

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region_name: str = "auto",
        public_url: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region_name = region_name or "auto"
        self.public_url = public_url.rstrip("/") if public_url else None
        self.base_dir = (
            cache_dir or (Path(__file__).resolve().parent.parent.parent / "storage" / "r2_cache")
        ).resolve()
        self._s3_client = None
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensures local cache directories exist."""
        for folder in ["videos", "faces", "temp"]:
            (self.base_dir / folder).mkdir(parents=True, exist_ok=True)

    @property
    def client(self):
        """Lazy initialization of boto3 client."""
        if self._s3_client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError:
                raise RuntimeError(
                    "boto3 is required for Cloudflare R2 / S3 storage. Run 'pip install boto3'."
                )

            s3_config = Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            )
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region_name,
                config=s3_config,
            )
        return self._s3_client

    async def save_upload(
        self,
        upload_file: UploadFile,
        subfolder: str,
        max_size_bytes: int,
        allowed_extensions: Set[str],
        allowed_mimes: Set[str],
        prefix: str = "file",
    ) -> FileStorageResult:
        """Validates stream into local cache, then replicates to Cloudflare R2 / S3."""
        local_service = LocalStorageService(base_dir=self.base_dir)
        local_result = await local_service.save_upload(
            upload_file=upload_file,
            subfolder=subfolder,
            max_size_bytes=max_size_bytes,
            allowed_extensions=allowed_extensions,
            allowed_mimes=allowed_mimes,
            prefix=prefix,
        )

        local_file_path = self.base_dir / local_result.storage_path
        try:
            extra_args = {"ContentType": local_result.content_type}
            self.client.upload_file(
                Filename=str(local_file_path),
                Bucket=self.bucket_name,
                Key=local_result.storage_path,
                ExtraArgs=extra_args,
            )
            logger.info("Persisted %s to R2/S3 bucket '%s'", local_result.storage_path, self.bucket_name)
        except Exception as e:
            logger.error("Failed to upload %s to R2/S3: %s", local_result.storage_path, e)
            if local_file_path.exists():
                local_file_path.unlink()
            raise

        return local_result

    async def save_bytes(
        self,
        data: bytes,
        subfolder: str,
        extension: str,
        prefix: str = "file",
        content_type: str = "image/jpeg",
        original_filename: str = "file.jpg",
    ) -> FileStorageResult:
        """Saves bytes to local cache and uploads directly to Cloudflare R2 / S3."""
        local_service = LocalStorageService(base_dir=self.base_dir)
        local_result = await local_service.save_bytes(
            data=data,
            subfolder=subfolder,
            extension=extension,
            prefix=prefix,
            content_type=content_type,
            original_filename=original_filename,
        )

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=local_result.storage_path,
                Body=data,
                ContentType=content_type,
            )
            logger.info(
                "Persisted %s bytes to R2/S3 bucket '%s' key '%s'",
                len(data),
                self.bucket_name,
                local_result.storage_path,
            )
        except Exception as e:
            logger.error("Failed to put object %s to R2/S3: %s", local_result.storage_path, e)
            raise

        return local_result

    def get_file_path(self, storage_path: str) -> Path:
        """
        Returns local filesystem Path for OpenCV/FFmpeg.
        If file was flushed from local ephemeral container disk, restores it from R2/S3 on demand.
        """
        local_path = (self.base_dir / storage_path).resolve()
        if not str(local_path).startswith(str(self.base_dir)):
            raise ValueError("Path traversal attempt detected.")

        if not local_path.exists() or local_path.stat().st_size == 0:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Local cache miss for %s; fetching from R2/S3 bucket '%s'", storage_path, self.bucket_name)
            try:
                self.client.download_file(
                    Bucket=self.bucket_name,
                    Key=storage_path,
                    Filename=str(local_path),
                )
                logger.info("Cached %s locally from R2/S3", storage_path)
            except Exception as e:
                logger.error("Failed to retrieve %s from R2/S3: %s", storage_path, e)
                raise FileNotFoundError(f"File '{storage_path}' not found in R2/S3 storage.")

        return local_path

    async def delete_file(self, storage_path: str) -> bool:
        """Deletes from R2/S3 and removes local cached copy."""
        deleted = False
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=storage_path)
            deleted = True
            logger.info("Deleted %s from R2/S3 bucket '%s'", storage_path, self.bucket_name)
        except Exception as e:
            logger.warning("Failed to delete %s from R2/S3: %s", storage_path, e)

        local_path = (self.base_dir / storage_path).resolve()
        if local_path.exists():
            try:
                local_path.unlink()
            except Exception as e:
                logger.warning("Failed to remove local file %s: %s", local_path, e)

        return deleted

    def get_download_url(self, storage_path: str) -> Optional[str]:
        """Returns direct public CDN URL or presigned download URL."""
        if self.public_url:
            return f"{self.public_url}/{storage_path}"
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": storage_path},
                ExpiresIn=3600,
            )
            return url
        except Exception as e:
            logger.warning("Failed to generate presigned URL for %s: %s", storage_path, e)
            return None


def get_storage_service() -> BaseStorageService:
    """Dependency provider for storage service. Auto-detects R2/S3 or LocalStorage."""
    from app.core.config import get_settings

    settings = get_settings()

    is_r2_or_s3 = (
        settings.STORAGE_BACKEND.lower() in ("r2", "s3")
        or bool(settings.R2_BUCKET_NAME)
    )

    if is_r2_or_s3 and settings.R2_BUCKET_NAME:
        endpoint = settings.S3_ENDPOINT_URL
        if not endpoint and settings.R2_ACCOUNT_ID:
            endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

        return S3R2StorageService(
            bucket_name=settings.R2_BUCKET_NAME,
            endpoint_url=endpoint,
            access_key_id=settings.R2_ACCESS_KEY_ID,
            secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION_NAME,
            public_url=settings.R2_PUBLIC_URL,
            cache_dir=settings.resolved_storage_dir / "r2_cache",
        )

    return LocalStorageService(base_dir=settings.resolved_storage_dir)
