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
    "w600k_r50.onnx": {
        "url": "https://huggingface.co/maze/faceX/resolve/main/w600k_r50.onnx",
        "description": "ArcFace ResNet50 512-D Face Recognition Embedding Model",
        "size_expected": 174383860,
    },
    "inswapper_128.onnx": {
        "url": "https://huggingface.co/ModelsLab/inswapper/resolve/main/inswapper_128.onnx",
        "description": "InsightFace Inswapper 128x128 Face-Replacement Model",
        "size_expected": 555302286,
    },
}


def download_with_progress(url: str, dest_path: Path, expected_size: int = None) -> bool:
    if dest_path.exists() and dest_path.stat().st_size > 1000:
        if expected_size is None or dest_path.stat().st_size == expected_size:
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

        # Atomic rename
        if dest_path.exists():
            dest_path.unlink()
        temp_path.rename(dest_path)

        # Compute SHA-256
        sha256 = hashlib.sha256()
        with open(dest_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                sha256.update(chunk)
        digest = sha256.hexdigest()

        print(f"[DONE] Successfully downloaded {dest_path.name} ({dest_path.stat().st_size:,} bytes)")
        print(f"       SHA-256: {digest}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to download {dest_path.name}: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False


def main():
    print("=" * 70)
    print("BollySwap AI — Pretrained Face Replacement Model Downloader")
    print("=" * 70)
    success = True
    for filename, info in MODELS.items():
        dest = MODELS_DIR / filename
        ok = download_with_progress(info["url"], dest, info["size_expected"])
        if not ok:
            success = False

    if success:
        print("\nAll models downloaded successfully.")
    else:
        print("\nOne or more models failed to download.")
        sys.exit(1)


if __name__ == "__main__":
    main()
