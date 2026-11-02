"""
Download script for BollySwap AI Face Replacement Models.
Downloads:
1. ArcFace 512-D identity feature extractor (w600k_r50.onnx)
2. Inswapper 128 Face-Swap neural model (inswapper_128.onnx)
Verifies SHA-256 checksums and saves license documentation.
"""

import hashlib
import os
import sys
import time
from pathlib import Path
import urllib.request

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "face_detection_yunet_2023mar.onnx": {
        "url": os.getenv(
            "YUNET_DOWNLOAD_URL",
            "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        ),
        "description": "OpenCV YuNet Face Detection Model",
        "size_expected": 232589,
        "sha256": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        "required_for_swap": False,
    },
    "w600k_r50.onnx": {
        "url": os.getenv(
            "ARCFACE_DOWNLOAD_URL",
            "https://huggingface.co/maze/faceX/resolve/main/w600k_r50.onnx",
        ),
        "description": "ArcFace ResNet50 512-D Face Recognition Embedding Model",
        "size_expected": 174383860,
        "sha256": "4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43",
        "required_for_swap": True,
    },
    "inswapper_128.onnx": {
        "url": os.getenv(
            "INSWAPPER_DOWNLOAD_URL",
            "https://huggingface.co/ModelsLab/inswapper/resolve/main/inswapper_128.onnx",
        ),
        "description": "InsightFace Inswapper 128x128 Face-Replacement Model",
        "size_expected": 555302286,
        "sha256": "0fa95f167682b4f61edf24f8d66c46b4ab130e8be058f00c8150e6d0170ca72f",
        "required_for_swap": True,
    },
}


def download_with_progress(
    url: str,
    dest_path: Path,
    expected_size: int = None,
    expected_sha256: str = None,
) -> bool:
    if dest_path.exists() and dest_path.stat().st_size > 1000:
        if expected_size is None or dest_path.stat().st_size == expected_size:
            # Check checksum if available
            if expected_sha256:
                sha = hashlib.sha256()
                with open(dest_path, "rb") as f:
                    while chunk := f.read(1024 * 1024):
                        sha.update(chunk)
                if sha.hexdigest() == expected_sha256:
                    print(f"[EXISTS & VERIFIED] {dest_path.name} ({dest_path.stat().st_size:,} bytes). Skipping.")
                    return True
                else:
                    print(f"[CHECKSUM MISMATCH] {dest_path.name} corrupted. Re-downloading...")
            else:
                print(f"[EXISTS] {dest_path.name} already exists ({dest_path.stat().st_size:,} bytes). Skipping.")
                return True
        else:
            print(f"[RE-DOWNLOAD] {dest_path.name} size mismatch ({dest_path.stat().st_size} vs {expected_size}).")

    temp_path = dest_path.with_suffix(".tmp")
    print(f"[DOWNLOADING] {dest_path.name} from {url}...")
    start_time = time.time()

    headers = {"User-Agent": "BollySwap-Downloader/1.0"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as resp, open(temp_path, "wb") as out_file:
            total_size = int(resp.headers.get("content-length", 0)) or expected_size or 0
            downloaded = 0
            chunk_size = 1024 * 1024  # 1 MB chunks

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)

                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    elapsed = time.time() - start_time
                    speed_mb = (downloaded / (1024 * 1024)) / max(elapsed, 0.001)
                    sys.stdout.write(
                        f"\r  -> {dest_path.name}: {downloaded / (1024*1024):.1f}/{total_size / (1024*1024):.1f} MB ({percent:.1f}%) @ {speed_mb:.1f} MB/s"
                    )
                    sys.stdout.flush()

            sys.stdout.write("\n")

        # Compute SHA-256 before accepting file
        sha256 = hashlib.sha256()
        with open(temp_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                sha256.update(chunk)
        digest = sha256.hexdigest()

        if expected_sha256 and digest != expected_sha256:
            print(f"[ERROR] SHA-256 verification failed for {dest_path.name}:")
            print(f"        Expected: {expected_sha256}")
            print(f"        Got:      {digest}")
            if temp_path.exists():
                temp_path.unlink()
            return False

        # Atomic rename
        if dest_path.exists():
            dest_path.unlink()
        temp_path.rename(dest_path)

        print(f"[DONE] Successfully verified and saved {dest_path.name} ({dest_path.stat().st_size:,} bytes)")
        print(f"       SHA-256: {digest}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to download {dest_path.name}: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False


def main():
    print("=" * 70)
    print("BollySwap AI — Pretrained Model Downloader & Validator")
    print("=" * 70)

    # Check if swap models should be downloaded
    face_swap_enabled = os.getenv("FACE_SWAP_ENABLED", "true").lower() in ("true", "1", "yes")
    detection_only = "--detection-only" in sys.argv or not face_swap_enabled

    if detection_only:
        print("Note: FACE_SWAP_ENABLED is false or --detection-only passed.")
        print("Downloading face detection model only (skipping large swap weights).\n")

    success = True
    for filename, info in MODELS.items():
        if detection_only and info.get("required_for_swap", False):
            continue

        dest = MODELS_DIR / filename
        ok = download_with_progress(
            info["url"],
            dest,
            info.get("size_expected"),
            info.get("sha256"),
        )
        if not ok:
            success = False

    if success:
        print("\nAll requested models downloaded and verified successfully.")
    else:
        print("\nOne or more models failed to download or verify.")
        sys.exit(1)


if __name__ == "__main__":
    main()

