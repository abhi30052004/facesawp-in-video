"""
Tests for Cloudflare R2 / AWS S3 persistent storage implementation.
Verifies file upload, download on cache miss, presigned URL generation,
and factory auto-detection.
"""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.core.config import Settings
from app.services.storage_service import (
    BaseStorageService,
    LocalStorageService,
    S3R2StorageService,
    get_storage_service,
)


@pytest.fixture
def local_tmp_path():
    p = Path("backend/storage/temp_test_r2")
    p.mkdir(parents=True, exist_ok=True)
    yield p
    shutil.rmtree(p, ignore_errors=True)


@pytest.fixture
def mock_s3_client():
    client = MagicMock()
    client.upload_file.return_value = None
    client.download_file.return_value = None
    client.put_object.return_value = None
    client.delete_object.return_value = None
    client.generate_presigned_url.return_value = "https://mock-presigned-r2.com/video.mp4?token=abc"
    return client


def test_s3_r2_storage_initialization(local_tmp_path):
    storage = S3R2StorageService(
        bucket_name="bollyswap-media",
        endpoint_url="https://mock-account.r2.cloudflarestorage.com",
        access_key_id="mock_key",
        secret_access_key="mock_secret",
        public_url="https://media.bollyswap.com",
        cache_dir=local_tmp_path / "cache",
    )
    assert storage.bucket_name == "bollyswap-media"
    assert storage.public_url == "https://media.bollyswap.com"
    assert (local_tmp_path / "cache" / "videos").exists()
    assert (local_tmp_path / "cache" / "faces").exists()


@pytest.mark.anyio
async def test_s3_r2_save_bytes(local_tmp_path, mock_s3_client):
    storage = S3R2StorageService(
        bucket_name="bollyswap-media",
        cache_dir=local_tmp_path / "cache",
    )
    storage._s3_client = mock_s3_client

    sample_data = b"RIFF____WEBPtest_data"
    result = await storage.save_bytes(
        data=sample_data,
        subfolder="faces",
        extension="webp",
        prefix="thumb",
        content_type="image/webp",
        original_filename="thumb.webp",
    )

    assert result.upload_id.startswith("thumb_")
    assert result.storage_path.startswith("faces/thumb_")
    assert result.size_bytes == len(sample_data)

    mock_s3_client.put_object.assert_called_once_with(
        Bucket="bollyswap-media",
        Key=result.storage_path,
        Body=sample_data,
        ContentType="image/webp",
    )

    cached_file = local_tmp_path / "cache" / result.storage_path
    assert cached_file.exists()
    assert cached_file.read_bytes() == sample_data


def test_s3_r2_get_file_path_cache_hit(local_tmp_path, mock_s3_client):
    storage = S3R2StorageService(
        bucket_name="bollyswap-media",
        cache_dir=local_tmp_path / "cache",
    )
    storage._s3_client = mock_s3_client

    test_file = local_tmp_path / "cache" / "videos" / "test.mp4"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_bytes(b"existing_video_content")

    resolved = storage.get_file_path("videos/test.mp4")
    assert resolved == test_file.resolve()
    mock_s3_client.download_file.assert_not_called()


def test_s3_r2_get_file_path_cache_miss(local_tmp_path, mock_s3_client):
    storage = S3R2StorageService(
        bucket_name="bollyswap-media",
        cache_dir=local_tmp_path / "cache",
    )
    storage._s3_client = mock_s3_client

    def fake_download(Bucket, Key, Filename):
        Path(Filename).write_bytes(b"downloaded_from_r2")

    mock_s3_client.download_file.side_effect = fake_download

    resolved = storage.get_file_path("videos/remote_video.mp4")
    assert resolved.exists()
    assert resolved.read_bytes() == b"downloaded_from_r2"
    mock_s3_client.download_file.assert_called_once()


@pytest.mark.anyio
async def test_s3_r2_delete_file(local_tmp_path, mock_s3_client):
    storage = S3R2StorageService(
        bucket_name="bollyswap-media",
        cache_dir=local_tmp_path / "cache",
    )
    storage._s3_client = mock_s3_client

    test_file = local_tmp_path / "cache" / "faces" / "delete_me.jpg"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_bytes(b"delete_me")

    ok = await storage.delete_file("faces/delete_me.jpg")
    assert ok is True
    assert not test_file.exists()
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket="bollyswap-media", Key="faces/delete_me.jpg"
    )


def test_s3_r2_get_download_url_public(local_tmp_path, mock_s3_client):
    storage = S3R2StorageService(
        bucket_name="bollyswap-media",
        public_url="https://media.bollyswap.com",
        cache_dir=local_tmp_path / "cache",
    )
    storage._s3_client = mock_s3_client

    url = storage.get_download_url("videos/master.mp4")
    assert url == "https://media.bollyswap.com/videos/master.mp4"
    mock_s3_client.generate_presigned_url.assert_not_called()


def test_s3_r2_get_download_url_presigned(local_tmp_path, mock_s3_client):
    storage = S3R2StorageService(
        bucket_name="bollyswap-media",
        public_url=None,
        cache_dir=local_tmp_path / "cache",
    )
    storage._s3_client = mock_s3_client

    url = storage.get_download_url("videos/master.mp4")
    assert url == "https://mock-presigned-r2.com/video.mp4?token=abc"
    mock_s3_client.generate_presigned_url.assert_called_once()


def test_get_storage_service_factory_r2():
    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value = Settings(
            STORAGE_BACKEND="r2",
            R2_BUCKET_NAME="production-bollyswap-r2",
            R2_ACCOUNT_ID="acc123",
            R2_ACCESS_KEY_ID="key123",
            R2_SECRET_ACCESS_KEY="sec123",
            STORAGE_DIR="storage",
        )
        storage = get_storage_service()
        assert isinstance(storage, S3R2StorageService)
        assert storage.bucket_name == "production-bollyswap-r2"
        assert storage.endpoint_url == "https://acc123.r2.cloudflarestorage.com"


def test_get_storage_service_factory_local():
    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value = Settings(
            STORAGE_BACKEND="local",
            R2_BUCKET_NAME=None,
            STORAGE_DIR="storage",
        )
        storage = get_storage_service()
        assert isinstance(storage, LocalStorageService)
